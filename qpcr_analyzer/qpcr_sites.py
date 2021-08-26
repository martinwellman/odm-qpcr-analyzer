#%%
"""
# qpcr_sites.py

Manages site information for Wastewater, using a sites info (Excel) file and a sites configuration (YAML) file.
The YAML file specifies the column names in the Excel file to retrieve info from, as well as descriptions of
each site sampling type (eg. rawWW in ODM maps to the description "Influent" (short description) or 
"Raw wastewater" (long description)).

## Usage

    sites = QPCRSites("sites.yaml", "sites.xlsx")
    siteid = sites.get_sample_siteid("o.08.20.21")          # eg: "o"
    sitetitle = sites.get_sample_site_title("o.08.20.21")   # eg: "Ottawa"
"""

from easydict import EasyDict
import pandas as pd
import numpy as np
import yaml
from qpcr_utils import rename_columns
import re

class QPCRSites(object):
    def __init__(self, config_file, sites_file=None):
        super().__init__()

        with open(config_file, "r") as f:
            self.config = EasyDict(yaml.safe_load(f))

        self.sites_df = None
        if sites_file:
            xl =  pd.ExcelFile(sites_file)
            self.sites_df = xl.parse(xl.sheet_names[0])
            self.sites_df.columns = [c.strip() for c in self.sites_df.columns]
            self.sites_df.dropna(subset=[])

            # Clean up column names
            all_columns = [c.column for c in self.config.columns.values()]
            rename_columns(self.sites_df, all_columns)

            # Make values lower case
            for c in self.config.columns.values():
                if c.get("make_lower", False):
                    self.sites_df[c.column] = self.sites_df[c.column].str.lower()

    def get_siteid(self, siteid):
        """Get the valid siteid. If siteid is not recognized then None is returned. Site ID aliases will also be mapped to the actual site ID.
        """
        return self.resolve_aliases(siteid)

    def get_site_region(self, siteid):
        return self.get_site_info(siteid, self.config.columns.region.column)

    def get_site_title(self, siteid):
        return self.get_site_info(siteid, self.config.columns.site_title.column)

    def get_siteids_with_shared_parentid(self, siteid):
        """Get all site IDs, as a list, that share the parent of the specified siteid.
        """
        parentid = self.get_site_parentid(siteid)
        return self.get_siteids_in_parentid(parentid)

    def get_siteids_in_parentid(self, parentid):
        """Get all site IDs (including aliases) that are a member of the specified parent ID.
        """
        if isinstance(parentid, (pd.Series, pd.DataFrame)):
            return self.run_map(parentid, self.get_siteids_in_parentid)

        if not parentid:
            return []

        filt = self.sites_df[self.config.columns.parentid.column].str.lower() == parentid.strip().lower()

        siteids = list(self.sites_df[filt][self.config.columns.siteid.column].unique())
        siteids = [s for s in siteids if s and not pd.isna(s)]
        aliasids = list(self.sites_df[filt][self.config.columns.siteid_aliases.column].unique())
        aliasids = [s for s in aliasids if s and not pd.isna(s)]

        siteids = list(dict.fromkeys(siteids + aliasids))

        return siteids

    def run_map(self, df, func, *args, **kwargs):
        """Call the function on each cell in the df (either a pd.Series or a pd.DataFrame). The parameters passed to the function are the cell contents 
        followed by args and kwargs. This is equivalent to calling map (for a pd.Series) or applymap (for a pd.DataFrame). The calls are not in-place,
        but the returned and modified pd.Series or pd.DataFrame can be used.
        """
        if isinstance(df, pd.Series):
            return df.map(lambda x: func(x, *args, **kwargs))
        elif isinstance(df, pd.DataFrame):
            return df.applymap(lambda x: func(x, *args, **kwargs))
        return df

    def get_site_siteid_aliases(self, siteid):
        """Get all aliases for the specified site ID. Aliases are IDs that are commonly used but that should be mapped to a standard ID
        eg. "gat" might be an alias for the proper site ID "g".
        """
        if isinstance(siteid, (pd.Series, pd.DataFrame)):
            return self.run_map(siteid, self.get_site_siteid_aliases)

        aliases = self.get_site_info(siteid, self.config.columns.siteid_aliases.column)
        return [a.strip() for a in aliases.split(",")]

    def get_site_parentid(self, siteid):
        return self.get_site_info(siteid, self.config.columns.parentid.column)

    def get_site_parent_title(self, siteid):
        return self.get_site_info(siteid, self.config.columns.parent_title.column)

    def get_site_sample_type(self, siteid):
        return self.get_site_info(siteid, self.config.columns.sample_type.column)

    def get_sample_siteid(self, sample_id):
        return self.get_site_info(self.get_siteid_from_sampleid(sample_id), self.config.columns.siteid.column)

    def get_sample_region(self, sample_id):
        return self.get_site_info(self.get_siteid_from_sampleid(sample_id), self.config.columns.region.column)

    def get_sample_site_title(self, sample_id):
        return self.get_site_info(self.get_siteid_from_sampleid(sample_id), self.config.columns.site_title.column)

    def get_sample_siteid_aliases(self, sample_id):
        if isinstance(sample_id, (pd.Series, pd.DataFrame)):
            return self.run_map(sample_id, self.get_sample_siteid_aliases)

        aliases = self.get_site_info(self.get_siteid_from_sampleid(sample_id), self.config.columns.siteid_aliases.column)
        if pd.isna(aliases) or not aliases:
            return None
        return [a.strip() for a in aliases.split(",")]

    def get_unknown_siteid(self):
        """Get the string ID to use for any unrecognized site.
        """
        return self.config.unknown_siteid

    def get_sample_parentid(self, sample_id):
        return self.get_site_info(self.get_siteid_from_sampleid(sample_id), self.config.columns.parentid.column)

    def get_sample_parent_title(self, sample_id):
        return self.get_site_info(self.get_siteid_from_sampleid(sample_id), self.config.columns.parent_title.column)

    def get_sample_sample_type(self, sample_id):
        return self.get_site_info(self.get_siteid_from_sampleid(sample_id), self.config.columns.sample_type.column)

    def get_type_description(self, sample_type):
        """Get a description of the ODM sample type (eg. "rawWW" -> "Raw wastewater")
        """
        if isinstance(sample_type, (pd.Series, pd.DataFrame)):
            return self.run_map(sample_type, self.get_type_description)

        info = self.get_sample_type_info(sample_type)
        return "" if info is None else info.description

    def get_type_short_description(self, sample_type):
        """Get a short description of the ODM sample type (eg. "rawWW" -> "Influent")
        """
        if isinstance(sample_type, (pd.Series, pd.DataFrame)):
            return self.run_map(sample_type, self.get_type_short_description)

        info = self.get_sample_type_info(sample_type)
        return "" if info is None else info.short_description

    def get_sample_type_info(self, sample_type):
        """Get the description dictionary for the ODM sample type. This is the array element in the
        sites.yaml file matching the sample_type, and contains a "description" and "shortDescription" key.
        """
        if isinstance(sample_type, (pd.Series, pd.DataFrame)):
            return self.run_map(sample_type, self.get_sample_type_info)

        if sample_type is None:
            return None

        sample_type = sample_type.strip().lower()
        matches = [info for info in self.config.descriptions if sample_type == info.type.strip().lower()]
        return None if len(matches) == 0 else matches[0]

    def get_siteid_from_sampleid(self, sample_id):
        if isinstance(sample_id, (pd.Series, pd.DataFrame)):
            return self.run_map(sample_id, self.get_siteid_from_sampleid)

        comps = sample_id.split(".")
        if len(comps) == 0:
            return None
        siteid = comps[0].strip()
        if self.config.columns.siteid.make_lower:
            siteid = siteid.lower()
        return siteid

    def resolve_aliases(self, siteid):
        if isinstance(siteid, (pd.Series, pd.DataFrame)):
            return self.run_map(siteid, self.resolve_aliases)

        lower_siteid = siteid.strip().lower()
        found_siteid = None
        matches = self.sites_df[self.config.columns.siteid.column].str.lower() == siteid
        if matches.sum() > 0:
            found_siteid = self.sites_df[self.config.columns.siteid.column][matches].iloc[0]

        if not found_siteid:
            for idx, (cur_siteid, aliases) in self.sites_df[[self.config.columns.siteid.column, self.config.columns.siteid_aliases.column]].iterrows():
                if pd.isna(aliases):
                    continue
                aliases = [a.strip().lower() for a in aliases.split(",")]
                if lower_siteid in aliases:
                    found_siteid = cur_siteid
                if lower_siteid == cur_siteid.strip().lower():
                    found_siteid = cur_siteid
                if found_siteid:
                    break
        if found_siteid and self.config.columns.siteid.make_lower:
            found_siteid = found_siteid.lower()
        return found_siteid

    def get_site_info(self, siteid, retrieve_col=None, default=None):
        """Get info (from the sites.xlsx file passed to the constructor) for the specified site ID (or alias).

        Parameters
        ----------
        siteid : str | pd.Series | pd.DataFrame
            The site ID or alias to retrieve.
        retrieve_col : str | list[str]
            The column(s) to retrieve. If None then all columns are retrieved.
        default : any
            The default value to use if the siteid is not recognized.
        
        Returns
        -------
        object | pd.Series | pd.DataFrame
            The requested info from the sites Excel file.
        """
        if isinstance(siteid, (pd.Series, pd.DataFrame)):
            return self.run_map(siteid, self.get_site_info, retrieve_col=retrieve_col)

        if not siteid:
            return default

        siteid = self.resolve_aliases(siteid)
        if siteid is None:
            return default
        siteid = siteid.strip().lower()

        # Find the matching site ID in the sites Excel file, return the value in retrieve_col
        match = self.sites_df[self.sites_df[self.config.columns.siteid.column].str.lower() == siteid]
        if len(match.index) == 0:
            return default
        match = match.iloc[0]
        if retrieve_col is None:
            return match
        match = match[retrieve_col]
        if isinstance(match, str):
            match = match.strip()

        return match

    def get_site_info_from_sample_id(self, sample_id, retrieve_col=None):
        siteid = self.get_siteid_from_sampleid(sample_id)
        return self.get_site_info(siteid, retrieve_col=retrieve_col)

    def get_region_column(self):
        return self.config.columns.region.column

    def get_site_title_column(self):
        return self.config.columns.site_title.column

    def get_siteid_column(self):
        return self.config.columns.siteid.column

    def get_siteid_aliases_column(self):
        return self.config.columns.siteid_aliases.column

    def get_parentid_column(self):
        return self.config.columns.parentid.column

    def get_parent_title_column(self):
        return self.config.columns.parent_title.column

    def get_sample_type_column(self):
        return self.config.columns.sample_type.column

    def get_parent_title(self, parent_id):
        if isinstance(parent_id, (pd.Series, pd.DataFrame)):
            return self.run_map(parent_id, self.get_parent_title)
        
        matches = self.sites_df[self.sites_df[self.config.columns.parentid.column].str.lower() == parent_id.strip().lower()]
        if len(matches.index) == 0:
            return parent_id
        return matches.iloc[0][self.config.columns.parent_title.column]

    def group_by_parentid(self, df, siteid_col, intersection_filter=None, always_include_filter=None):
        """Make groups of the rows in a pd.DataFrame using the site IDs in the DataFrame. All site IDs with a common
        parent ID are grouped together.

        Parameters
        ----------
        df : pd.DataFrame
            The DataFrame to group.
        siteid_col : str
            The column in the df that contains the site IDs.
        intersection_filter : pd.Series | pd.DataFrame
            A filter into df specifying which items in df to group. All other items are ignored for grouping purposes.
        always_include_filter : pd.Series | pd.DataFrame
            A filter into df specifying which additional items to include in each group.

        Returns
        -------
        list
            A list of groups. Each item in the list is one group, and consists of [dict, group_df], where dict contains group info such as the
            parentSiteID (str) and the parentSiteTitle (str). group_df is all the items in the group.
        """
        groups = []
        siteids = df[siteid_col]
        all_siteids = []

        for parent_id, parent_group in self.sites_df.groupby(self.config.columns.parentid.column):
            cur_siteids = parent_group[self.config.columns.siteid.column]
            all_siteids.extend(list(cur_siteids))
            children = siteids.isin(cur_siteids)
            if intersection_filter is not None:
                children = children & intersection_filter
            if children.sum() == 0:
                continue

            cur_filt = children
            if always_include_filter is not None:
                cur_filt = children | always_include_filter
            
            groups.append(({
                "parentSiteID" : parent_id,
                "parentSiteTitle" : self.get_parent_title(parent_id)
            }, df[cur_filt]))

        # Add unrecognized sites
        site_unknowns = ~siteids.isin(all_siteids)
        if site_unknowns.sum() > 0:
            cur_filt = site_unknowns
            if intersection_filter is not None:
                cur_filt = cur_filt & intersection_filter
            if always_include_filter is not None:
                cur_filt = cur_filt | always_include_filter
            cur_df = df[cur_filt]
            groups.append(({
                "parentSiteID" : self.config.unknown_siteid,
                "parentSiteTitle" : self.config.unknown_siteid,
            }, cur_df))
            
        return groups

    def split_off_siteid_number(self, siteid):
        """Get the site ID in the passed in siteid (resolving aliases), and if it is immediately followed by a number (which sometimes people
        include in a sample ID) get that number, split it from the site ID, and include it separately in the return value.

        Parameters
        ----------
        siteid : str | pd.Series | pd.DataFrame

        Returns
        -------
        list | pd.Series | pd.DataFrame
            The site IDs as a list of length 1 or 2, where the items[0] is the site ID and items[1] is the number. eg. If "uo_np" is
            a valid site ID, and "up_np5" is passed in as siteid, then ["uo_np", 5] is returned. If instead "uo_np" is passed in, then
            ["uo_np"] is returned. If the siteid is not recognized then [siteid] is returned.
        """
        if isinstance(siteid, (pd.Series, pd.DataFrame)):
            return self.run_map(siteid, self.split_off_siteid_number)

        match = self.get_siteid(siteid)
        if not match:
            trailing_numbers = ""
            cur_siteid = siteid
            while len(cur_siteid) > 0:
                prev_siteid = cur_siteid
                # Remove one digit from the end of cur_siteid                    
                cur_trailing_number = re.findall("[0-9]$", cur_siteid)
                cur_siteid = re.sub("[0-9]$", "", cur_siteid)
                # If no digits are at the end of cur_siteid (ie. unchanged) then we're done
                if cur_siteid == prev_siteid:
                    break
                trailing_numbers = f"{cur_trailing_number[0]}{trailing_numbers}"
                match = self.get_siteid(cur_siteid) # = self.sites_df[self.sites_df[self.config.sites_excel.siteid_col] == cur_siteid]
                if match:
                    return[match, trailing_numbers]
        return [self.get_siteid(siteid) or siteid]

if __name__ == "__main__":
    sites = QPCRSites("sites.yaml", "sites.xlsx")
    # df = pd.DataFrame({"a" : ["vc2.07.08.21", "o.07.08.21", "q.12"]})
    # print(sites.get_sample_siteid("vc2.07.08.21"))
    # types = sites.get_sample_sample_type(df)
    # print(sites.get_type_short_description(types))
    print(sites.get_siteids_with_shared_parentid("g"))
