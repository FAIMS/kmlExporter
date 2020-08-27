sudo apt-get update
sudo apt-get install python spatialite-bin libimage-exiftool-perl libspatialite-dev python-pip jhead python-numpy -y

sudo pip install python-magic fastkml shapely ordereddict lxml numpy
export PATH="$HOME/.rbenv/bin:$PATH" 
eval "$(rbenv init -)"

rbenv install 2.5.0
rbenv local 2.5.0
gem install sqlite3 antlr3
if lsb_release -d -s | grep -q 16.04; then
	sudo apt-get install libsqlite3-mod-spatialite
fi