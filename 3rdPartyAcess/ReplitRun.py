from os.path import dirname as up

botRun = up("bot.py")

from threading import Thread
from flask import Flask
from flask_restful import Api, Resource

import psutil
import platform

flk = Flask(__name__)
api = Api(flk)

def _run():
  flk.run(debug=False, host='0.0.0.0', port=8080)


class MainResource(Resource):
  def get(self):
    ram = psutil.virtual_memory()
    return {"os": platform.platform(), 
    "arch": platform.architecture(),
    "machkind": platform.machine(),
    "ram": {
      "free": ram.available,
      "used": ram.used
      }
    }

api.add_resource(MainResource, "/")
if __name__ == "__main__":
  threa = Thread(target=_run)
  threa.start()
  exec(open(botRun).read())
  
