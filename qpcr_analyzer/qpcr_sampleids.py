#%%
"""
# qpcr_sampleids.py

Creates sample IDs in the correct format.

## Usage
    
    sampleids = QPCRSampleIDs("qpcr_sampleids.yaml", "qpcr_sites.yaml", "qpcr_sites.xlsx")
    
    df = pd.DataFrame({
        "sampleid" : ["h1", "uo_na.01.05.2022", "h.01.22.2021"],
        "date" : ["Aug 1, 2021", "Apr 3 2022", "Mar 2 2022"]
    })
    df = sampleids.make_all_sample_ids(df, "sampleid", "date", target_sample_id_col="newid", target_match_sample_id_col="matchid")

    # df is:
    #         sampleid         date           newid         matchid
    # 0                h1  Aug 1, 2021    h.1.08.01.21      h.08.01.21
    # 1  uo_na.01.05.2022   Apr 3 2022  uo_na.01.05.22  uo_na.01.05.22
    # 2      h.01.22.2021   Mar 2 2022      h.01.22.21      h.01.22.21
    
    # Result is: ('uo_na.3.03.03.22', 'uo_na.03.03.22')
    sample_id, match_sample_id = sampleids.make_sample_id("uo_na3", "March 3rd, 2022")
"""

from easydict import EasyDict
import pandas as pd
import yaml
import argparse
from datetime import datetime
import re
from qpcr_sites import QPCRSites

class QPCRSampleIDs(object):
    def __init__(self, config, sites_config, sites_file):
        with open(config, "r") as f:
            self.config = yaml.safe_load(f)
        self.sites = QPCRSites(sites_config, sites_file)
        
    def make_all_sample_ids(self, df, sample_id_col, sample_date_col, *, target_sample_id_col=None, target_match_sample_id_col=None, inplace=True):
        """Convert all sample IDs (with optional dates) in a DataFrame to the correct format, and optionally also set
        the match sample ID (see make_sample_id).

        Args:
            df (pd.DataFrame): The DataFrame that contains the sample IDs (and optionally dates) and that also receives
                the formatted sample IDs. This DataFrame is modified in place.
            sample_id_col (str): The column in df that contains the string sample IDs to format.
            sample_date_col (str|None): The column in df that contains the dates of the sample IDs. If the sample ID does not
                have a date then we append the values in this column as a date.
            target_sample_id_col (str, optional): The column in df to save the formatted sample ID in. If None then sample_id_col receives the
                formatted sample IDs. Defaults to None.
            target_match_sample_id_col (str, optional): The column in df to save the formatted match sample IDs in. If None then the match sample IDs
                are not set. Defaults to None.
            inplace (bool, optional): If True then modify the df DataFrame. If False then keep df unchanged and return a copy with
                the formatted sample IDs.

        Returns:
            df: The DataFrame with
        """
        if not inplace:
            df = df.copy()
        target_sample_id_col = target_sample_id_col or sample_id_col
        df[target_sample_id_col] = df.apply(lambda x: self.make_sample_id(x[sample_id_col], x[sample_date_col] if sample_date_col else None), axis=1)
        if target_match_sample_id_col is not None:
            df[target_match_sample_id_col] = df[target_sample_id_col].map(lambda x: x[1])
        df[target_sample_id_col] = df[target_sample_id_col].map(lambda x: x[0])
        return df

    def make_sample_id(self, sample_id, sample_date):
        """Make a sample ID, in the correct format, from the specified sample ID and date. The date can be None.

        Parameters
        ----------
        sample_id : str
            The sample ID we want to clean and turn into a sample ID in the correct format.
        sample_date : str|datetime
            A string date or datetime for the sample ID. We will try to extract the date form the sample_id, but if it can't
            then we will use this date for the sample ID. sample_date will be passed to the datetime.datetime constructor.
            Can be None.
        
        Returns
        -------
        sample_id : str
            The final sample ID to use
        match_sample_id : str
            A sample ID, very similar to sample_id, that should be used to match values between the extracted DataFrame and the samples file.
            This sample ID is typically sample_id but with a few components removed. For example, uo_na2.05.01.2022 would have
            a resulting sample_id of uo_na.2.05.01.22 and a match_sample_id of uo_na.05.01.22. The 2 is sometimes added to indicate
            this is run #2 of the sample. In the samples log file we would search for uo_na.05.01.22, instead of the other
            format with a 2.
        """
        sample_id = str(sample_id).strip().lower()

        # Remove any trailing _r (or _r#). These are reruns (ie. samples that were previously run, but had to be rerun due to some error)
        # We'll re-add the _r# at the end.
        rerun = re.search("_r[0-9]*$", sample_id)
        if rerun is None:
            rerun = re.search("(?<=[0-9])r[0-9]*$", sample_id)
        if rerun:
            rerun = rerun[0]
            sample_id = sample_id[:-len(rerun)]
            if len(rerun) > 0 and rerun[0] != "_":
                rerun = f"_{rerun}"

        # All numbers should be preceded by a dot, rather than an underscore
        sample_id = re.sub("_(?=[0-9])", ".", sample_id)
        
        #  Replace spaces and dashes with dots
        sample_id = re.sub("[ -]", ".", sample_id)

        # Replace text months to integers
        for month_num, months in enumerate(self.config["month_mapper"]):
            # Sort by month length, to match longer month first (eg. "April" will match with "April" to get 04,
            # instead of with "Apr" to get "04il")
            months.sort(key=len, reverse=True)
            for month in months:
                sample_id = re.sub(month, f"{month_num+1}.", sample_id, flags=re.IGNORECASE)
        sample_id = re.sub("\.\.", ".", sample_id)

        # Number groups are preceded by a dot and trailed by a dot or end of string
        # Add leading 0 to number groups that are 1 character long
        sample_id = re.sub("(?<=\.)([0-9])(?=\.|$)", "0\\1", sample_id)
        # Reduce length of number groups down to last 2 digits if longer than 2 digits
        sample_id = re.sub("(?<=\.)([0-9]*([0-9][0-9]))(?=\.|$)", "\\2", sample_id)

        # All letter groups should be preceded by an underscore (except for PS).
        sample_id = re.sub("\.(?=[A-Za-z])", "_", sample_id)
        sample_id = re.sub("_ps", ".ps", sample_id)

        # Last numbers should be mm.dd.yy
        comps = sample_id.split(".")
        num_trailing_digit_groups = 0
        for comp in comps[::-1]:
            try:
                _ = int(comp)   # Will throw exception if comp isn't a string integer
                num_trailing_digit_groups += 1
            except:
                break

        if num_trailing_digit_groups == 2:
            # @TODO: What should we do if only month and day are provided in the sample ID (ie. no year)?
            # Likely want to keep it with only month and day (ie. do nothing here)
            pass
            
            # # Add the default year since only the month and day are available in the sample ID
            # default_year = str(self.config.default_year)[-2:]
            # sample_id = f"{sample_id}.{default_year}"
            # default_year = "21"
            # sample_id = f"{sample_id}.{default_year}"
        elif num_trailing_digit_groups < 2 and sample_date is not None:
            # There aren't enough trailing digits to form a sample date, so extract the sample date from sample_date_col
            try:
                date = pd.to_datetime(sample_date) or ""
                if isinstance(date, pd.Timestamp):
                    date = date.strftime("%m.%d.%y")
                else:
                    date = str(date)
            except:
                date = ""
            if len(date) > 0:
                sample_id = f"{sample_id}.{date}"

        match_sample_id = sample_id

        # Site ID is the first match. Sometimes an extra number is added at the end of the site ID
        # and so can't be found in the samples file. For those items, try removing the numbers
        # (one at a time) at the end and see if that will match a site ID, and use it if it does.
        comps = sample_id.split(".")
        if num_trailing_digit_groups < len(comps) and self.sites is not None: #self.sites_df is not None:
            siteid = comps[0]
            siteid_and_number = self.sites.split_off_siteid_number(siteid)
            sample_id = ".".join([*siteid_and_number, *comps[1:]])
            match_sample_id = ".".join([siteid_and_number[0], *comps[1:]])
        else:
            if self.sites is not None:
                comps[0] = self.sites.get_siteid(comps[0]) or comps[0]
            match_sample_id = ".".join(comps)

        # Readd _r rerun
        # match_sample_id = re.sub("\.ps", "", match_sample_id)
        if rerun:
            sample_id = f"{sample_id}{rerun}"
            # match_sample_id = f"{match_sample_id}{rerun}"

        return sample_id, match_sample_id

if __name__ == "__main__":
    if "get_ipython" in globals():
        opts = EasyDict({
            "config" : "qpcr_sampleids.yaml",
            "sites_config" : "qpcr_sites.yaml",
            "sites_file" : "qpcr_sites.xlsx",
        })
    else:
        args = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        args.add_argument("--config", type=str, help="Main config file", default="qpcr_extracter.yaml")
        args.add_argument("--sites_config", type=str, help="Sites config file", default="sites.yaml")
        args.add_argument("--sites_file", type=str, help="Sites data file", default="sites.xslx")
        opts = args.parse_args()

    tic = datetime.now()
    samples = QPCRSampleIDs(opts.config, opts.sites_config, opts.sites_file)
    
    # print(samples.make_sample_id("uo_na3", "March 3rd, 2022"))

    df = pd.DataFrame({
        "sampleid" : ["h1", "uo_na.01.05.2022", "h.01.22.2021", "o_12.21.21r"],
        "date" : ["Aug 1, 2021", "Apr 3 2022", "Mar 2 2022", None]
    })
    df = samples.make_all_sample_ids(df, "sampleid", "date", target_sample_id_col="newid", target_match_sample_id_col="matchid")
    
    print(df)
    
    print("Finished!")
