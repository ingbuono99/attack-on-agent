import logging
from aiohttp_jinja2 import template
from aiohttp_jinja2 import template, web
from app.service.auth_svc import for_all_public_methods, check_authorization
from app.utility.base_world import BaseWorld
from plugins.attack.app.attack_svc import AttackService


@for_all_public_methods(check_authorization)
class AttackGUI(BaseWorld):

    def __init__(self, services, name, description):
        self.name = name
        self.description = description
        self.services = services
        self.attack_svc = AttackService(services)

        self.auth_svc = services.get('auth_svc')
        self.log = logging.getLogger('attack_gui')

    @template('attack.html')
    async def splash(self, request):
        return dict(name=self.name, description=self.description)

    # Add functions here that the front-end will use

    async def sendability(self, request):
        data = await request.json()
        links = await self.attack_svc.send_ability(paw=data['paw'], ability_id=data['ability_id'], obfuscator = 'plain-text', facts = ()); 
        self.log.info("Operazione eseguita...link_id: %s", links[0].id)
        links_id = [None] * len(links)
        i = 0
        for link in links:
            links_id[i] = link.id
            self.log.info(links_id[i])
            i = i + 1
        
        return web.json_response(links_id)  #PER ORA RITORNO SOLO GLI ID, FORSE SAREBBE MEGLIO RITORNARE GLI OGGETTI??

    async def newoperation(self, request):
        data = await request.json()
        operation = await self.attack_svc.new_operation(name = data['name']);
        return web.Response(text = operation.id)
    
    async def newlink(self, request):
       data = await request.json()
       access = dict(access=tuple(await self.auth_svc.get_permissions(request)))
       link = await self.attack_svc.new_potential_link(operation_id = data['operation_id'], paw = data['paw'], ability_id = data['ability_id'],  access = access)
       return web.Response(text = link.id)