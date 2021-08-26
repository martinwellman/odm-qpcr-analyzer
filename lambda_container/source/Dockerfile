FROM public.ecr.aws/lambda/python:3.8

ADD app .

RUN yum update -y
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN yum install -y ghostscript
RUN yum install -y git
# Install nano text editor for testing, makes it easier to debug if we need to SSH in
RUN yum install -y nano

# Get location of OpenPYXL and ghostscript packages, so we can modify them.
# Variables do not persist between RUN commands, but files do, so save the locations to separate files.
RUN echo $(python3 -c "import openpyxl, os; print(os.path.dirname(openpyxl.__file__));" 2> /dev/null) > OPENPYXL_DIR.txt
RUN echo $(python3 -c "import ghostscript, os; print(os.path.dirname(ghostscript.__file__));" 2> /dev/null) > GHOSTSCRIPT_DIR.txt
RUN DIR=$(cat OPENPYXL_DIR.txt);    echo "OPENPYXL_DIR:     $DIR"
RUN DIR=$(cat GHOSTSCRIPT_DIR.txt); echo "GHOSTSCRIPT_DIR:  $DIR"

# Fixes for Python 3.8.10:
# - openpyxl in /var/lang/lib/python3.8/site-packages/openpyxl/worksheet/_reader.py:
#   throws an unhandled exception type when reading an XLSX file and encountering an invalid date.
#   Replace "except ValueError" with "except", to handle all exception types.
# - Ghostscript in /var/lang/lib/python3.8/site-packages/ghostscript/_gsprint.py
#   Line 262 in init_with_args has incorrect argument types (strings not allowed, expects bytes/bytearrays)
RUN DIR=$(cat OPENPYXL_DIR.txt); find "$DIR" -name _reader.py | xargs sed -i.bak 's/except ValueError/except/g'
RUN DIR=$(cat GHOSTSCRIPT_DIR.txt); find "$DIR" -name _gsprint.py | xargs sed -i.bak 's/ArgArray(\*argv)/ArgArray(*[a.encode("UTF-8") for a in argv])/g'

# Add support for saving both a formula string and a corresponding value of an Excel cell, by setting the calculated_value property
# attached_data allows attaching Pandas data rows from the ODM to spreadsheet cells
RUN DIR=$(cat OPENPYXL_DIR.txt); find "$DIR/cell" -name cell.py | xargs sed -i.bak "s/'_value',\s*$/'_value', 'calculated_value', 'attached_data',/g"
RUN DIR=$(cat OPENPYXL_DIR.txt); find "$DIR/cell" -name cell.py | xargs sed -i.bak "s/[(]'row', 'column'[)]/('row', 'column', 'calculated_value', 'attached_data')/g"
RUN DIR=$(cat OPENPYXL_DIR.txt); find "$DIR/cell" -name _writer.py | xargs sed -i.bak "s/^            value = None/            value = getattr(cell, 'calculated_value', None)\n            if isinstance(value, str):\n                if len(value) > 0 and value[0] == '#' and value[-1] in ['!', '?']:\n                    el.set('t', 'e')\n                else:\n                    el.set('t', 'str')/g"
RUN DIR=$(cat OPENPYXL_DIR.txt); find "$DIR/cell" -name _writer.py | xargs sed -i.bak "s/^                    value = None/                    raise RuntimeError('Must implement custom calculated_value for LXML')/g"

# RUN git clone https://github.com/jeandavidt/ODM-Import.git
RUN git clone https://github.com/martinwellman/ODM-Import.git
RUN cd ODM-Import && pip3 install -e .

CMD ["app.handler"]