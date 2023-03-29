import logging
from app.utility.base_service import BaseService
from app.objects.c_operation import Operation
from app.objects.c_adversary import Adversary, AdversarySchema
import json

class AttackService(BaseService):  #importo BaseService perchè sta là il metodo get_service()
    def __init__(self, services):
        self.services = services
        self.file_svc = services.get('file_svc')
        self.data_svc = services.get('data_svc')
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
    
    #To make possible the spanning of abilities on the agents, we need to create a new operation with no adversary profile specified 
    #Then, to this operation, we'll add all the potential links
    async def new_operation(self, name):
        #find the default source
        defaultSourceId = 'ed32b9c3-9593-4c33-b0db-e2007315096b'  # basic fact source
        sources = await self.data_svc.locate("sources")
        for source in sources:
            if source.id == defaultSourceId:
                src = source
        self.log.info("source trovata: %s " %src.name)

        #find the atomic planner
        planners = await self.data_svc.locate('planners')
        for p in planners:
            if p.name == "atomic":
                planner = p
        self.log.info("planner trovato: %s" %planner.name)

        #Create a new empty adversary profile
        adv = Adversary.load(dict(adversary_id='ad-hoc', name='ad-hoc', description='an empty adversary profile',
                                      atomic_ordering=[]))
        AdversarySchema().dump(adv) #?????NECESSARIO???

        #create and save the new operation
        operation = Operation(adversary = adv, name = name, source = src, planner = planner)
        await self.data_svc.store(operation)

        return operation