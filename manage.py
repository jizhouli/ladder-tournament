# -*- coding: utf-8 -*-
# from gevent.monkey import patch_all; patch_all()

import os
import yaml
import os.path
import tempfile

from flask.ext.script import Manager, Server
from flask.ext.migrate import MigrateCommand

# update zaih.app to your appname
from src.app import create_app

app = create_app()
manager = Manager(app)


@manager.command
def test():
    """Run the tests."""
    import subprocess
    code = subprocess.call(['py.test', 'tests', '--cov',
                            'lt', '--verbose'])
    return code


@manager.command
def fixture():
    pass


def dirfile(path):
    tmpfile = tempfile.NamedTemporaryFile(delete=False)
    for roots, dirs, files in os.walk(path):
        yml_files = [f for f in files if f.endswith('.yml')]
        for fn in yml_files:
            fn = '/'.join([path, fn])
            with open(fn, 'r') as f:
                tmpfile.write(f.read())
    tmpfile.seek(0)
    tmpfile.close()
    return tmpfile.name


class Loader(yaml.Loader):

    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(Loader, self).__init__(stream)

    def include(self, node):
        is_delete = False
        filename = os.path.join(self._root, self.construct_scalar(node))
        if os.path.isdir(filename):
            print filename
            filename = dirfile(filename)
            print filename
            is_delete = True
        with open(filename, 'r') as f:
            return yaml.load(f, Loader)
        if is_delete and os.path.exists(filename):
            os.unlink(filename)

Loader.add_constructor('!include', Loader.include)


@manager.option('-s', '--source', help='source file for convert', default='docs/base.yml')
@manager.option('-d', '--dist', help='file name that you will save', default='docs/v1.yml')
def swagger_merge(source, dist):
    with open(source, 'r') as f:
        data = yaml.load(f, Loader)
    with open(dist, 'w') as f:
        f.write(yaml.dump(data))
    print 'merge success!'


# swagger_py_codegen -s  docs/apis.yml  apis_src -p zhinsta
@manager.option('-s', '--swagger', help='Swagger doc file.', default='docs/v1.yml')
@manager.option('-p', '--package', help='Package name / application name', default='lt')
@manager.option('-d', '--dist', help='Package name / application name', default='.')
def swagger_py_codegen(swagger, dist, package):
    if dist:
        command = 'swagger_py_codegen -s %s %s -p %s --ui --spec' % (swagger, dist, package)
    else:
        command = 'swagger_py_codegen -s %s -p %s --ui --spec' % (swagger, package)
    print command
    os.system(command)
    # copy genarate code to lt
    print 'code generate success!'


manager.add_command('server', Server(host='0.0.0.0', port='8140',
                                     use_reloader=True, processes=4))
manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()
