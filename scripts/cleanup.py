import os
import glob
for app in glob.glob('applications/*'):
    if os.path.isdir(app):
        print app
        errors = glob.glob('%s/errors/*' % app)
        print '- deleting %s error files' % len(errors)
        for error in errors:
            os.unlink(error)
        sessions = glob.glob('%s/sessions/*' % app)
        print '- deleting %s session files' % len(sessions)
        for session in sessions:
            os.unlink(session)
