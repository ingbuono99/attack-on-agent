from app.utility.base_world import BaseWorld
from plugins.attack.app.attack_gui import AttackGUI
from plugins.attack.app.attack_api import AttackAPI

name = 'Attack'
description = 'Choose which ability to send on which agent'
address = '/plugin/attack/gui'
access = BaseWorld.Access.RED


async def enable(services):
    app = services.get('app_svc').application
    attack_gui = AttackGUI(services, name=name, description=description)
    app.router.add_static('/attack', 'plugins/attack/static/', append_version=True)
    app.router.add_route('GET', '/plugin/attack/gui', attack_gui.splash)
    app.router.add_route('POST', '/plugin/attack/sendability', attack_gui.sendability)
    app.router.add_route('POST', '/plugin/attack/newoperation', attack_gui.newoperation)

    attack_api = AttackAPI(services)
    # Add API routes here
    app.router.add_route('POST', '/plugin/attack/mirror', attack_api.mirror)

