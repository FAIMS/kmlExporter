sudo apt-get update
sudo apt-get install spatialite-bin libimage-exiftool-perl libspatialite-dev python-pip jhead -y

sudo -H pip install python-magic fastkml shapely

if lsb_release -d -s | grep -q 16.04; then
	sudo apt-get install libsqlite3-mod-spatialite
fi