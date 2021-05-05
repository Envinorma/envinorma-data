apt -y update
apt -y install git
apt -y install screen
git clone https://github.com/Envinorma/envinorma-data.git
cd envinorma-data
apt -y install python3-pip
pip3 install virtualenv
virtualenv venv 
source venv/bin/activate
apt-get -y remove ocrmypdf
apt-get -y update
apt-get -y install \
    ghostscript \
    icc-profiles-free \
    liblept5 \
    libxml2 \
    pngquant \
    python3-pip \
    tesseract-ocr \
    tesseract-ocr-fra \
    zlib1g
pip3 install -r requirements.txt
pip3 install ipython==7.19.0
cp src/config_template.ini src/config.ini
cd src
X='COPY COMMAND'
screen -d -m bash -c "$X" -S ocr