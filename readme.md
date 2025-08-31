## A very basic web server for the ESG app

The ESG works by reading a config file (`config.yaml`) that details assets to be modelled, models to use and *the inputs* for those models (etc). Allowing the config file to specify where the input files is, complicates matters for the deployment to the cloud. In this application, the `config.yaml` file that is selected for upload with be modified before it is saved. In particular input and output paths will be overwritten with the values `UPLOAD_FOLDER` and `DOWNLOAD_FOLDER` from `app.py`. If the original `config.yaml` has `paths.fileNamesWithPaths` set to `true`, this webserver will throw an error because I have been to lazy to change each file. 

To cater for both local and cloud deployments, an environmental variable is used. It is only necessary to set this variable (see below) in the cloud environment as it is set to local if the variable does not exist.

NOTE to azure folders. I am assuming the username in azure is `azureuser`.

### Copying to Azure
1. SSH to the Azure VM: `ssh -i ~/.ssh/ESGVM_key.pem azureuser@20.16.201.44`
2. Create an environmental variable that `app.py` will use to check we are running in azure: `echo 'export APP_ENV=production' >> ~/.bashrc`  
`source ~/.bashrc`
3. Install the linux tool dos2unix: `sudo apt install dos2unix`

4. Install pip for Python 3: `sudo apt install -y python3-pip`
5. Install venv so you can create virtual environments: `sudo apt install -y python3-venv`
6. Get to the correct folder (I am assuming /home/azureuser/ESGFrontEnd/ Also make sure the subfolder inputs and outputs exists)
7. Create and virtual environment: `python3 -m venv env`
8. activate it: `source env/bin/activate`
9. Install dependencies: `pip install Flask`, `pip install pyyaml`
10. From your *local shell* copy the Flask code:
`scp -r -i ~/.ssh/ESGVM_key.pem /home/steven/code/ESGFrontEnd/app.py azureuser@20.16.201.44:/home/azureuser/ESGFrontEnd/`
`scp -r -i ~/.ssh/ESGVM_key.pem /home/steven/code/ESGFrontEnd/templates/* azureuser@20.16.201.44:/home/azureuser/ESGFrontEnd/templates/`
11. We are going to run the Flask app in a gunicorn server:  
`pip3 install gunicorn`  
`gunicorn -w 4 -b 0.0.0.0:8000 app:app --timeout 120` (note the extended timeout which is required in case the output file is large)

12. In the Azure portal, make sure port 8000 is open: Go to the VM / Networking and Create port rule. Change the Desination port range to 8000, make it TCP and any source. Don't change any other default options
13. Now you should be able to navigate to http://20.16.201.44:8000/ (or your IP address at port 8000) and you should see the app running.