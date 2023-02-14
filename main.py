import os
import argparse
import multiprocessing
import gunicorn.app.base
from dotenv import dotenv_values
from database import create_tables


def create_secret(_args):
    """
    Creates a secret and stores it in a .env file in the current working directory
    Use `python main.py create-secret --help` for more options
    Args:
        _args: The parsed command line arguments
    """

    config = dotenv_values('.env')

    # No .env file exists or no secret key has been set
    if config is None or config.get('SECRET') is None:
        with open('.env', 'a') as f:
            f.write(f'SECRET={os.urandom(24).hex()}')

        print(f"Secret stored at {os.path.abspath('.env')}")
    else:
        print("A secret already exists. Use --overwrite to create a new secret.")
        if _args.overwrite:
            with open('.env', 'w') as f:
                for key, value in config.items():
                    if key == 'SECRET':
                        value = os.urandom(24).hex()
                    f.write(f"{key}={value}")
        else:
            print("dont update secret")


parser = argparse.ArgumentParser(description='CLI to setup our blogging API.')
subparsers = parser.add_subparsers()

secret_parser = subparsers.add_parser('create-secret',
                                      help="Writes a suitable secret key to a .env file in the current working directory.")
secret_parser.add_argument('--overwrite', action='store_true', help="Overwrite the present secret value.")
secret_parser.set_defaults(func=create_secret)

db_parser = subparsers.add_parser('create-db', help="Creates the tables and the databses for the project")
db_parser.set_defaults(func=create_tables)


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


# def handler_app(environ, start_response):
#     from app import app
#
#     status = '200 OK'
#     response_headers = [
#         ('Content-Type', MediaTypes.json),
#     ]
#
#     start_response(status, response_headers)
#
#     return app(environ, start_response)


class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, self_app, self_options=None):
        self.options = self_options or {}
        self.application = self_app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == '__main__':
    from app import app
    options = {
        'bind': '%s:%s' % ('127.0.0.1', '8080'),
        'workers': number_of_workers(),
        'worker_class': 'uvicorn.workers.UvicornWorker',
        'reload': True
    }
    StandaloneApplication(app, options).run()
