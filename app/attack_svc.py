import logging
import uuid
from app.utility.base_service import BaseService
from app.objects.c_operation import Operation
from app.objects.c_ability import AbilitySchema
from app.objects.c_adversary import Adversary, AdversarySchema
from app.objects.secondclass.c_executor import Executor, ExecutorSchema
from app.api.v2.responses import JsonHttpBadRequest, JsonHttpForbidden, JsonHttpNotFound
from app.objects.secondclass.c_link import Link
from app.utility.base_world import BaseWorld
from base64 import b64encode
from app.api.v2.managers.operation_api_manager import OperationApiManager


class AttackService(OperationApiManager):  
    def __init__(self, services):
        
        #self.file_svc = services.get('file_svc')
        #self.data_svc = services.get('data_svc')
        #self.log = logging.getLogger('attack_svc')
        super().__init__(services)
        self.services = services

    async def foo(self):
        return 'bar'

    # Add functions here that call core service
    
    async def send_ability(self, paw, ability_id, obfuscator, facts=()):
        new_links = []
        #converted_facts = [Fact(trait=f['trait'], value=f['value']) for f in data.get('facts', [])]
        for agent in await self._data_svc.locate('agents', dict(paw=paw)):
            self.log.info('Tasking %s with %s' % (paw, ability_id))
            links = await agent.task(
                abilities=await self._data_svc.locate('abilities', match=dict(ability_id=ability_id)),
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
        sources = await self._data_svc.locate("sources")
        for source in sources:
            if source.id == defaultSourceId:
                src = source
        self.log.info("source trovata: %s " %src.name)

        #find the atomic planner
        planners = await self._data_svc.locate('planners')
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
        await operation.update_operation_agents(self.services)
        await self._data_svc.store(operation)

        return operation
    

    #Datas that has to be send to create_potential_link includes an executor, that has to have 2 parameters:
    #1) 'name' such as 'sh', 'bash' etc...
    #2) 'command', so we have to retrieve the command associated with the needed ability and selected exectuor name
    async def new_potential_link(self, operation_id, paw , ability_id, access):
        
        agents_list = await self._data_svc.locate('agents')
        for ag in agents_list:
            if ag.paw == paw:
                agent = ag
        self.log.info("paw %s" %agent.paw)
      
        #Retrieve ability by given id
        abilities = await self._data_svc.locate('abilities')
        for ab in abilities:
            if ab.ability_id == ability_id:
                ability = ab
        self.log.info("ability %s" %ability.ability_id)
        executor = ''
        self.log.info("name: %s" %agent.executors[0])
        #retrieve ability exectuor 
        for ex in ability.executors:
            if ex.name == agent.executors[0]:
                executor = ex
        self.log.info('exectuor found, command: %s' %executor.command)
      
        #vars needed to convert executor class in a dictionary. vars adds some useless parameters that we get rid of with that for loop.
        #We MUST remove these parameters, otherwise the ExecutorSchema().load  in build_executor() is going to fail.
        dictEx = {k: v for k, v in vars(executor).items() if not k.startswith('_')}
        #same thing for ability
        dictAb = {k: v for k, v in vars(ability).items() if not k.startswith('_')}

        #construct data dictionary
        data = dict(paw= paw,executor =  dictEx, ability = dictAb, platform = None, executors = None)
        
        #method override
        OperationApiManager.build_ability = self.build_ability

        #create a new potential link
        link = await self.create_potential_link(operation_id, data, access)

        #This one returning is actually link.display
        return link

    #Need to override this function to add that data.pop('tags') line that causes problems. Tags, in fact, is not present in AbilitySchema.
    def build_ability(self, data: dict, executor: Executor):
        if not data.get('ability_id'):
            data['ability_id'] = str(uuid.uuid4())
        if not data.get('tactic'):
            data['tactic'] = 'auto-generated'
        if not data.get('technique_id'):
            data['technique_id'] = 'auto-generated'
        if not data.get('technique_name'):
            data['technique_name'] = 'auto-generated'
        if not data.get('name'):
            data['name'] = 'Manual Command'
        if not data.get('description'):
            data['description'] = 'Manual command ability'
        data['executors'] = [ExecutorSchema().dump(executor)]
        #Added line
        data.pop('tags')
        ability = AbilitySchema().load(data)
        return ability

    



    
    