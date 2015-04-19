"This script will work fine for a few cases 'by default':"
" - completely CLEAN WS2012R2 host"
" - python 2.7 installed in the default path"
" - wfasctgi installed on the default path"
"It'll install web2py under the default website "
" You can use it as a boilerplate to automate your deployments"
" but it still is released AS IT IS. "
"BIG FAT WARNING: It will install a bunch of dependecies
Inspect the source before executing it"
""
""
$ErrorActionPreference = 'stop'

$REALLY_SURE = Read-Host "Do you want to start with web2py deployment? [y/N]"
if (!@('y', 'Y') -contains $REALLY_SURE) {
    "Ok, Exiting without doing anything"
    exit 1
} 
#setting root folder
$rootfolder = $pwd

### utilities - start
function ask_a_question($question) {
  $response = Read-Host "$question [Y/n]" 
  if (@('Y', 'y', '', $null) -contains $response) {
    return $true
  } else {
        return $false
    }
}

function unzip_me {
    #Load the assembly
    [System.Reflection.Assembly]::LoadWithPartialName("System.IO.Compression.FileSystem") | Out-Null
    #Unzip the file
    [System.IO.Compression.ZipFile]::ExtractToDirectory($pathToZip, $targetDir)
}


### utilities - end

#install 4.5 that is needed for a bunch of things anyway
Install-WindowsFeature Net-Framework-45-Core

#fetch web2py
$web2py_url = 'http://www.web2py.com/examples/static/web2py_src.zip'
$web2py_file = "$pwd\web2py_src.zip"
if (!(Test-Path $web2py_file)) {
    (new-object net.webclient).DownloadFile($web2py_url, $web2py_file)
}
#Load the assembly
[System.Reflection.Assembly]::LoadWithPartialName("System.IO.Compression.FileSystem") | Out-Null
#Unzip the file
[System.IO.Compression.ZipFile]::ExtractToDirectory($web2py_file, $pwd)

#features installation (IIS, needed modules, python, chocolatey, etc)
$installfeatures = ask_a_question('Do you want to install needed features?')

if ($installfeatures) {
    Install-WindowsFeature Web-Server,Web-Default-Doc,Web-Static-Content,Web-Http-Redirect,Web-Http-Logging,Web-Request-Monitor,`
        Web-Http-Tracing,Web-Stat-Compression,Web-Dyn-Compression,Web-Filtering,Web-Basic-Auth,Web-Windows-Auth,Web-AppInit,`
        Web-CGI,Web-WebSockets,Web-Mgmt-Console,Web-Net-Ext45
}

$copy_web2py = ask_a_question("Copy web2py to the default website root?")
if ($copy_web2py) {
    Import-Module WebAdministration
    $available_websites = Get-Website
    if ($available_websites[0] -eq $null) {
        $default_one = $available_websites
    } else {
        $default_one = $available_websites[0]
    }
    $iis_root =  [System.Environment]::ExpandEnvironmentVariables($default_one.PhysicalPath)
    Copy-Item "$rootfolder\web2py\*" $iis_root -Recurse
    $rootfolder = $iis_root
    $acl = (Get-Item $rootfolder).GetAccessControl('Access')
    $identity = "BUILTIN\IIS_IUSRS"
    $fileSystemRights = "Modify"
    $inheritanceFlags = "ContainerInherit, ObjectInherit"
    $propagationFlags = "None"
    $accessControlType = "Allow"
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity, $fileSystemRights, $inheritanceFlags, $propagationFlags, $accessControlType)
    $acl.SetAccessRule($rule)
    Set-Acl $rootfolder $acl
}

$create_cert = ask_a_question("Do you want to create a self-signed SSL cert?")
if ($create_cert) {
  $cert = New-SelfSignedCertificate -DnsName ("localtest.me","*.localtest.me") -CertStoreLocation cert:\LocalMachine\My
  $rootStore = Get-Item cert:\LocalMachine\Root
  $rootStore.Open("ReadWrite")
  $rootStore.Add($cert)
  $rootStore.Close();
  Import-Module WebAdministration
  Set-Location IIS:\SslBindings
  New-WebBinding -Name "Default Web Site" -IP "*" -Port 443 -Protocol https
  $cert | New-Item 0.0.0.0!443
  Set-Location $pwd
}

"checking for chocolatey"
if (Get-Command "choco.exe" -ErrorAction SilentlyContinue) 
{ 
   "chocolatey found"
} else {
  "installing chocolatey"
  (new-object net.webclient).DownloadString('https://chocolatey.org/install.ps1') | iex
}
"installing url-rewrite"
choco install UrlRewrite
$pythonexe = Read-Host 'Python.exe path [C:\Python27\python.exe]'
if (($pythonexe -eq '') -or ($pythonexe -eq $null)) {
    $pythonexe = 'C:\Python27\python.exe'
}
if (!(Test-Path $pythonexe)) {
    "ERROR: python executable not found"
  $pythonwanted = ask_a_question("do you want to install it automatically?")
    
  if ($pythonwanted) {
    choco install webpicmd
    WebpiCmd.exe /Install /Products:WFastCgi_21_279
    $pythonexe = 'C:\Python27\python.exe'
  }
  else {
    exit 1
  }
    
}
$wfastcgipath = Read-Host 'wfastcgi.py path [C:\Python27\Scripts\wfastcgi.py]'
if (($wfastcgipath -eq '') -or ($wfastcgipath -eq $null)) {
    $wfastcgipath = 'C:\Python27\Scripts\wfastcgi.py'
}

if (-not (Test-Path $wfastcgipath)) {
    "ERROR: wfastcgi.py not found"
  
  $wfastcgiwanted = ask_a_question("do you want to install it automatically?")
  if ($wfastcgiwanted) {
    choco install webpicmd
    WebpiCmd.exe /Install /Products:WFastCgi_21_279
  } else {
    exit 1
  }
}
$pythondir = Split-Path c:\python27\python.exe
#installing dependencies
$env:Path = $env:Path + ";$pythondir;$pythondir\Scripts"

pip install pypiwin32

$PW = Read-Host 'Web2py Admin Password'

$appcmdpath = "$env:windir\system32\inetsrv\appcmd.exe"

& $appcmdpath set config /section:system.webServer/fastCGI "/+[fullPath='$pythonexe', arguments='$wfastcgipath']"
& $appcmdpath unlock config -section:system.webServer/handlers

& cd $rootfolder
& $pythonexe -c "from gluon.main import save_password; save_password('$PW',443)"

$webconfig_template = Join-Path $rootfolder "examples\web.config"
$destination = Join-Path $rootfolder "web.config"
$scriptprocessor = 'scriptProcessor="{0}|{1}"' -f $pythonexe, $wfastcgipath

(Get-Content $webconfig_template) | Foreach-Object {$_ -replace 'scriptProcessor="SCRIPT_PROCESSOR"', $scriptprocessor} | where {$_ -ne ""} | Set-Content $destination
""
"Installation finished. Web2py is available either on http://localhost/ or at https://localtest.me/"
""
