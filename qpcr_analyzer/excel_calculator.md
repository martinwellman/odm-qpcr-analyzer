# excel_calculator.py

This module calculate literal values for all formulas in an Excel file loaded with openpyxl. The values are calculated with pycel, and custom support is added for saving these values to disk when saving the Excel file.

This requires a custom version of openpyxl with the following changes:

1. find /var/lang/lib/python3.8/site-packages/openpyxl/cell -name cell.py | xargs sed -i.bak "s/'_value',/'_value', 'calculated_value', 'attached_data',/g"
1. find /var/lang/lib/python3.8/site-packages/openpyxl/cell -name cell.py | xargs sed -i.bak "s/'row', 'column'/'row', 'column', 'calculated_value', 'attached_data'/g"
1. find /var/lang/lib/python3.8/site-packages/openpyxl/cell -name _writer.py | xargs sed -i.bak "s/^            value = None/            value = getattr(cell, 'calculated_value', None)\n            if isinstance(value, str):\n                if len(value) > 0 and value[0] == '#' and value[-1] in ['!', '?']:\n                    el.set('t', 'e')\n                else:\n                    el.set('t', 'str')/g"
1. find /var/lang/lib/python3.8/site-packages/openpyxl/cell -name _writer.py | xargs sed -i.bak "s/^                    value = None/                    raise RuntimeError('Must implement custom calculated_value for LXML')/g"

**NOTE:** These changes should be made in a branch sometime in the future, rather than made directly on the master openpyxl.

Openpyxl uses the \__slots__ attribute for cell classes, preventing us from adding custom attributes to objects of the class. We therefore modify both openpyxl.Cell and openpyxl.MergedCell with an additional `calculated_value` member in the classes' \__slots__. The `attached_data` member also added by the above is not for calculating formula values, but is instead used by other QPCR utilities to attach pd.DataFrame rows to cells (`attached_data` is a list of rows), so can be removed if not required. `calculated_value` is the literal value, and is saved to the Workbook when serializing to disk.

## Usage

    add_excel_calculated_values(wb)
    wb.save("output_file.xlsx")

For some unknown reason, we sometimes need to first save `wb` to disk then reload it before calling `add_excel_calculated_value`.
Until this is fixed, it is recommended to always save and reload first:

    wb.save("output_file.xlsx")
    wb = openpyxl.load_workbook("output_file.xlsx")
    add_excel_calculated_values(wb)
    wb.save("output_file.xlsx")

## Additional @excel_helper() Functions

The functions with the @excel_helper() attributes in excel_calculator are additional Excel function evaluators that pycel does not support out-of-the-box. eg. `rsq(Y, X)` is for the Excel `RSQ` function, for calculating the R-squared of a linear regression.
