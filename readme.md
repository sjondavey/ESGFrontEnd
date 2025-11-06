## A very basic web server for the ESG app

The ESG works by reading a config file (`config.yaml`) that details assets to be modelled, models to use and *the inputs* for those models (etc). Allowing the config file to specify where the input files is, complicates matters for the deployment to the cloud. In this application, the `config.yaml` file that is selected for upload with be modified before it is saved. In particular input and output paths will be overwritten with the values `UPLOAD_FOLDER` and `DOWNLOAD_FOLDER` from `app.py`. If the original `config.yaml` has `paths.fileNamesWithPaths` set to `true`, this webserver will throw an error because I have been to lazy to change each file. 

To cater for both local and cloud deployments, an environmental variable is used. It is only necessary to set this variable (see below) in the cloud environment as it is set to local if the variable does not exist.

NOTE to azure folders. I am assuming the username in azure is `azureuser`.

### Running locally
From the terminal, run `gunicorn -w 4 -b 0.0.0.0:8000 app:app --timeout 120` (note the extended timeout which is required in case the output file is large). Navigate to `http://localhost:8000/`

### Running to Azure
1. Set up the VM  
a. SSH to the Azure VM: `ssh -i ~/.ssh/ESGVM_key.pem azureuser@20.16.201.44`  
b. Create an environmental variable that `app.py` will use to check we are running in azure:   
`echo 'export APP_ENV=production' >> ~/.bashrc`  
`source ~/.bashrc`  
c. Install pip for Python 3: `sudo apt install -y python3-pip`  
d. Install venv so you can create virtual environments: `sudo apt install -y python3-venv`  

2. Clone the git repo and set it up
```  
git clone https://github.com/sjondavey/ESGFrontEnd.git
cd ESGFrontEnd
mkdir inputs
mkdir outputs
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
If you only want to update from the github repo:
```
git fetch origin
git reset --hard origin/master
```   


3. We are going to run the Flask app in a gunicorn server:  
```
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app --timeout 120
```  
(note the extended timeout which is required in case the output file is large)

4. In the Azure portal, make sure port 8000 is open: Go to the VM / Networking and Create inbound port rule. Change the Destination port range to 8000, make it TCP and any source. Don't change any other default options
5. Now you should be able to navigate to http://20.16.201.44:8000/ (or your IP address at port 8000) and you should see the app running.


### Mapping esg.aleph-one.co to the Azure Server
1. Add a DNS record on GoDaddy  
Log in to GoDaddy and go to My Products → DNS for your domain.  
Under Records, click Add.  
Set the record type to A.  
Name: esg  
Value: your Azure VM's public IP (only the IP, no http:// or :8000)
TTL: default (1 hour is fine).  
After saving, DNS propagation can take a few minutes to a few hours.  

2. Configure your Azure VM to serve the app for that subdomain  
a. install NGINX  
`sudo apt update`  
`sudo apt install nginx`

b. Create a service file:  
`sudo nano /etc/systemd/system/esg.service`  

Paste this (adjust paths for your project):
```
[Unit]
Description=Gunicorn instance to serve ESG Flask app
After=network.target

[Service]
User=azureuser
Group=azureuser
WorkingDirectory=/home/azureuser/ESGFrontEnd
Environment="PATH=/home/azureuser/ESGFrontEnd/env/bin"
ExecStart=/home/azureuser/ESGFrontEnd/env/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 app:app
Environment=APP_ENV=production
Environment="LD_LIBRARY_PATH=/home/azureuser/AutoESG/lib"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
```
Save. Then
```
sudo systemctl daemon-reexec
sudo systemctl enable esg
sudo systemctl start esg
sudo systemctl status esg
```

3. NGINX config for the subdomain
Create a new config file:  
`sudo nano /etc/nginx/sites-available/esg`
Paste this:  
server {
    listen 80;
    server_name esg.aleph-one.co;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
Enable it:  
```
sudo ln -s /etc/nginx/sites-available/esg /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```
At this point, your Flask app should be reachable at http://esg.aleph-one.co

4. Enable HTTPS (Let's Encrypt)
Install certbot:   
`sudo apt install certbot python3-certbot-nginx -y`
Run:  
`sudo certbot --nginx -d esg.aleph-one.co`  
Choose option 2 (redirect HTTP to HTTPS).  
This will automatically edit your NGINX config to use SSL.

If you close down the service, to restart it
```
sudo systemctl daemon-reexec
sudo systemctl restart esg
sudo journalctl -u esg -f
```
