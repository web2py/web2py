import os
import subprocess
import codecs


#--- BZR: changelog information
def write_changelog_bzr(repo_path, output_dir, 
                                        output_file='bzr_revision_log.txt', 
                                        target_encoding='utf-8'):
    """Write the bzr changelog to a file which can then be included in the documentation
    """

    bzr_logfile_path = os.path.join(output_dir, output_file)
    bzr_logfile = codecs.open(bzr_logfile_path, 'w', encoding=target_encoding)
    try:
        p_log = subprocess.Popen(('bzr log --short'), 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
        (stdout, stderr) = p_log.communicate()
        bzr_logfile.write(stdout)
    finally:
        bzr_logfile.close()
    #UnicodeDecodeError: 'ascii' codec can't decode byte 0x81 in position 2871: ordinal not in range(128)
    
    # like bzr version-info --format python > vers_test.py



#--- BZR: version info

def write_version_info_bzr(repo_path, output_dir, output_file='_version.py'):
    """Write the version information from BZR repository into a version file.
    
    Parameters
    ----------
    repo_path : string
        Path to the BZR repository root
    repo_path : string
        Path to the output directory where the version info is saved
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    output_file : string
        output file name
    
    Returns
    -------
    p_info : subprocess_obj
        contents of the `func:`suprocess.Popen` returns
    
    """
    bzr_version_filepath = os.path.join(output_dir, output_file)
    bzr_version_file = open(bzr_version_filepath, 'w')
    p_info = subprocess.Popen(('bzr version-info --format python'), 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
    (stdout, stderr) = p_info.communicate()
    bzr_version_file.write(stdout)
    bzr_version_file.close()
    
    return p_info

    
#--- auto generate documentation

def autogenerate_package_doc(script_path, dest_dir, 
                                                    package_dir,                                                    
                                                    doc_header,
                                                    suffix='rst',
                                                    overwrite=False):
    """Autogenerate package API ReSt documents
    
    """
    print script_path
    if overwrite: 
        force = '--force' 
    p_apidoc = subprocess.Popen(('python', script_path, 
                                                '--dest-dir='+dest_dir, 
                                                '--suffix='+suffix,                                                 
                                                '--doc-header='+doc_header,
                                                force,  
                                                package_dir), bufsize=-1)
    'sphinxext\local\generate_modules_modif.py --dest-dir=source\contents\lib\auxilary\generated  --suffix=rst --force --doc-header=Auxilary ..\..\modules_local\auxilary'
    
    return p_apidoc


if __name__ == "__main__":
    repo_path = os.path.join('..', '.')
    output_dir = os.path.join('.')
    write_changelog_bzr(repo_path, output_dir, output_file='changelog.txt')
