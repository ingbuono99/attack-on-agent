import logging
from app.utility.base_service import BaseService

class AttackService(BaseService):  #importo BaseService perchè sta là il metodo get_service()
    def __init__(self, services):
        self.services = services
        self.file_svc = services.get('file_svc')
        self.log = logging.getLogger('attack_svc')

    async def foo(self):
        return 'bar'

    # Add functions here that call core service
    
    async def send_ability(self, paw, ability_id, obfuscator, facts=()):
        new_links = []
        #converted_facts = [Fact(trait=f['trait'], value=f['value']) for f in data.get('facts', [])]
        self.log.info("qua arriva2" )
        for agent in await self.get_service('data_svc').locate('agents', dict(paw=paw)):
            self.log.info("AGENTTT", agent )
            self.log.info('Tasking %s with %s' % (paw, ability_id))
            links = await agent.task(
                abilities=await self.get_service('data_svc').locate('abilities', match=dict(ability_id=ability_id)),
                obfuscator=obfuscator,
                facts=facts # facts = converted_facts
            )
            self.log.info("links", links)
            new_links.extend(links)
        return new_links
