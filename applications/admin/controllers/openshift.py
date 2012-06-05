import os
from distutils import dir_util
from git import *

def deploy():
    apps = sorted(file for file in os.listdir(apath(r=request)))#if regex.match(file))
    form = SQLFORM.factory(
        Field('osrepo',default='/tmp',label='Path to local openshift repo root.',
              requires=EXISTS(error_message=T('directory not found'))),
        Field('osname',default='web2py',label='WSGI reference name'),
        Field('applications','list:string',
              requires=IS_IN_SET(apps,multiple=True),
              label=T('web2py apps to deploy')))

    cmd = output = errors= ""
    if form.accepts(request,session):
        try:
            kill()
        except:
            pass
        
        ignore_apps = [item for item in apps \
                           if not item in form.vars.applications]
        regex = re.compile('\(applications/\(.*')
        w2p_origin = os.getcwd()
        osrepo = form.vars.osrepo
        osname = form.vars.osname
        #Git code starts here
        repo = Repo(form.vars.osrepo)
        index = repo.index
        assert repo.bare == False

        for i in form.vars.applications:
            appsrc = os.path.join(os.getcwd(),'applications',i)
            appdest = os.path.join(osrepo,'wsgi',osname,'applications',i)
            dir_util.copy_tree(appsrc,appdest)
            #shutil.copytree(appsrc,appdest)
            index.add(['wsgi/'+osname+'/applications/'+i])
            new_commit = index.commit("Deploy from Web2py IDE")                             #<--- COMMIT WORKED.. Next.. on to actual push.
        
        origin = repo.remotes.origin
        origin.push
        origin.push()
        #Git code ends here
    return dict(form=form,command=cmd)
        
class EXISTS(object):
    def __init__(self, error_message='file not found'):
        self.error_message = error_message
    def __call__(self, value):
        if os.path.exists(value):
            return (value,None)
        return (value,self.error_message)
