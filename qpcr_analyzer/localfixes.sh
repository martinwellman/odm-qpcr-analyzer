#!/bin/bash

# Retrieve OpenPYXL package directory
OPENPYXL_DIR=$(python3 -c "import openpyxl, os; print(os.path.dirname(openpyxl.__file__));" 2> /dev/null)
if [ "$?" != "0" -o "$OPENPYXL_DIR" == "" ]; then
    echo "The Python package openpyxl is not installed. Please install it by running"
    echo "    pip3 install openpyxl"
    exit 1
fi

# Retrieve Ghostscript package directory
GHOSTSCRIPT_DIR=$(python3 -c "import ghostscript, os; print(os.path.dirname(ghostscript.__file__));" 2> /dev/null)
if [ "$?" != "0" -o "$GHOSTSCRIPT_DIR" == "" ]; then
    echo "The Python package ghostscript is not installed. Please install it by running"
    echo "    pip3 install python3-ghostscript"
    exit 1
fi

echo "OPENPYXL_DIR:     ${OPENPYXL_DIR}"
echo "GHOSTSCRIPT_DIR:  ${GHOSTSCRIPT_DIR}"

find "$OPENPYXL_DIR" -name _reader.py | xargs sed -i.bak 's/except ValueError/except/g'
find "$GHOSTSCRIPT_DIR" -name _gsprint.py | xargs sed -i.bak 's/ArgArray(\*argv)/ArgArray(*[a.encode("UTF-8") for a in argv])/g'

# Add support for saving both a formula string and a corresponding value of an Excel cell, by setting the calculated_value property
# attached_data allows attaching Pandas data rows from the ODM to spreadsheet cells
find "$OPENPYXL_DIR/cell" -name cell.py | xargs sed -i.bak "s/'_value',\s*$/'_value', 'calculated_value', 'attached_data',/g"
find "$OPENPYXL_DIR/cell" -name cell.py | xargs sed -i.bak "s/[(]'row', 'column'[)]/('row', 'column', 'calculated_value', 'attached_data')/g"
find "$OPENPYXL_DIR/cell" -name _writer.py | xargs sed -i.bak "s/^            value = None/            value = getattr(cell, 'calculated_value', None)\n            if isinstance(value, str):\n                if len(value) > 0 and value[0] == '#' and value[-1] in ['!', '?']:\n                    el.set('t', 'e')\n                else:\n                    el.set('t', 'str')/g"
find "$OPENPYXL_DIR/cell" -name _writer.py | xargs sed -i.bak "s/^                    value = None/                    raise RuntimeError('Must implement custom calculated_value for LXML')/g"

echo "Finished applying fixes to OpenPYXL and Ghostscript"