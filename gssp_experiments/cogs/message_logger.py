from gssp_experiments.client_tools import ClientTools

class Controls():
    def __init__(self, client):
        self.client = client
        self.client_tools = ClientTools(client)
    
    async def on_message(self, message):
        print(message)
        return await self.client_tools.process_message(message)

def setup(client):
    client.add_cog(Controls(client))
