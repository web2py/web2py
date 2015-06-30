from setuptools.command import easy_install
import pkg_resources

def install(module_names):
    for name in module_names:
        try:
            pkg_resources.require(name)
        except pkg_resources.DistributionNotFound:
            easy_install.main( ["-U",name] )
            pkg_resources.require(name)
