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
import json

class AttackService(BaseService):  #importo BaseService perchè sta là il metodo get_service().
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
        for agent in await self.get_service('data_svc').locate('agents', dict(paw=paw)):
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
    

    #Datas that has to be send to create_potential_link includes an executor, that has to have 2 parameters:
    #1) 'name' such as 'sh', 'bash' etc...
    #2) 'command', so we have to retrieve the command associated with the needed ability and selected exectuor name
    async def new_potential_link(self, operation_id, paw , ability_id, access):
        
        agents_list = await self.data_svc.locate('agents')
        for ag in agents_list:
            if ag.paw == paw:
                agent = ag
        self.log.info("paw %s" %agent.paw)
      
        #Retrieve ability by given id
        abilities = await self.data_svc.locate('abilities')
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
        self.log.info('execturo trovato, comando: %s' %executor.command)
      
        #vars needed to convert executor class in a dictionary. vars adds some useless parameters that we get rid of with that for loop.
        #We MUST remove these parameters, otherwise the ExecutorSchema().load  in build_executor() is going to fail.
        dictEx = {k: v for k, v in vars(executor).items() if not k.startswith('_')}
        #same thing for ability
        dictAb = {k: v for k, v in vars(ability).items() if not k.startswith('_')}

        #construcd data dictionary
        data = dict(paw= paw,executor =  dictEx, ability = dictAb, platform = None, executors = None)
        

        link = await self.create_potential_link(operation_id, agent, data, access)
        return link


    async def create_potential_link(self, operation_id, agent, data: dict, access: BaseWorld.Access):
        self.validate_link_data(data)
        operation = await self.get_operation_object(operation_id, access)
        if data['executor']['name'] not in agent.executors:
            raise JsonHttpBadRequest(f'Agent {agent.paw} missing specified executor')
        encoded_command = self._encode_string(agent.replace(self._encode_string(data['executor']['command']),
                                              file_svc=self.services['file_svc']))
        executor = self.build_executor(data=data.pop('executor', {}), agent=agent)
        ability = self.build_ability(data=data.pop('ability', {}), executor=executor)
        link = Link.load(dict(command=encoded_command, plaintext_command=encoded_command, paw=agent.paw, ability=ability, executor=executor,
                              status=operation.link_status(), score=data.get('score', 0), jitter=data.get('jitter', 0),
                              cleanup=data.get('cleanup', 0), pin=data.get('pin', 0),
                              host=agent.host, deadman=data.get('deadman', False), used=data.get('used', []),
                              relationships=data.get('relationships', [])))
        
        link.apply_id(agent.host)
        await operation.apply(link)
        #maybe better to return link.display in the future
        return link
    

    async def get_operation_object(self, operation_id: str, access: dict):
        self.log.info("get_operation_object")
        try:
            operation = (await self.data_svc.locate('operations', {'id': operation_id}))[0]
        except IndexError:
            raise JsonHttpNotFound(f'Operation not found: {operation_id}')
        if operation.match(access):
            return operation
        raise JsonHttpForbidden(f'Cannot view operation due to insufficient permissions: {operation_id}')
    
    def build_executor(self, data: dict, agent):
        if not data.get('timeout'):
            data['timeout'] = 60
        data['platform'] = agent.platform
        executor = ExecutorSchema().load(data)
        return executor
    
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
        #Delete tags attribute, not present in AbilitySchema
        data.pop('tags')
        ability = AbilitySchema().load(data)
        return ability
    
    def validate_link_data(self, link_data: dict):
        self.log.info("validate_link_data")
        if not link_data.get('executor'):
            raise JsonHttpBadRequest('\'executor\' is a required field for link creation.')
        if not link_data['executor'].get('name'):
            raise JsonHttpBadRequest('\'name\' is a required field for link executor.')
        if not link_data['executor'].get('command'):
            raise JsonHttpBadRequest('\'command\' is a required field for link executor.')
        if not link_data.get('paw'):
            raise JsonHttpBadRequest('\'paw\' is a required field for link creation.')
        
    @staticmethod
    def _encode_string(s):
        return str(b64encode(s.encode()), 'utf-8')

    #QUI ANDRANNO LE FUNZIONI PER RECUPERARE I RISULTATI, VEDI SEMPRE FILE operation_api_manager.py
    #Altrimenti valuta di andare a leggerli direttamente da javascript, come fa il plugin Access

    
    