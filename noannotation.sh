#!/bin/bash

# Load RVM into a shell session *as a function*
export PATH="$HOME/.rbenv/bin:$PATH" 
eval "$(rbenv init -)"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
# echo $DIR
cd $2

ruby $DIR/string_formatter_tester.rb $1/db.sqlite3 $DIR/noannotation.format > $3/noannotation.out

