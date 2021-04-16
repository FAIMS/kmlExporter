sudo apt-get update
sudo apt-get install python spatialite-bin libimage-exiftool-perl libspatialite-dev python-pip jhead python-numpy -y

sudo pip install python-magic fastkml shapely ordereddict lxml numpy
export PATH="$HOME/.rbenv/bin:$PATH" 
eval "$(rbenv init -)"

if rbenv local | grep -q '2.5.6' ; then

echo "2.5.6 installed"
else

cd /home/faims/.rbenv/plugins/ruby-build && git pull && cd -

rbenv install 2.5.6
#rbenv local 2.5.6
bundler install

fi

if lsb_release -d -s | grep -q 16.04; then
	sudo apt-get install libsqlite3-mod-spatialite
fi