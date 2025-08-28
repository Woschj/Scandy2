sudo rsync -av --delete --exclude '__pycache__' --exclude '*.pyc' /home/woschj/Scandy2/app/ /opt/scandy/app/
sudo systemctl restart scandy.service
journalctl -u scandy.service -n 40 -xe --no-pager