# Example 2: adds user input and detects intents.

import watson_developer_cloud
import plugins.config as config 

# Set up Assistant service.
service = watson_developer_cloud.AssistantV2(
    iam_apikey = config.APIKEY, # replace with API key
    version = '2018-09-20'
)

assistant_id = config.ASSISTANTID # replace with assistant ID

# Create session.
session_id = service.create_session(
    assistant_id = assistant_id
).get_result()['session_id']

# Initialize with empty value to start the conversation.
user_input = ''


# Main input/output loop
#while user_input != 'quit':
def procesa_watson(user_input):

    # Send message to assistant.
    response = service.message(
        assistant_id,
        session_id,
        input = {
            'text': user_input
        }
    ).get_result()

    # If an intent was detected, print it to the console.
    if response['output']['intents']:
        res = response['output']['intents'][0]['intent']
        #print(str(res))
    else:
        res = "Disculpa, no te entendí."



    # Print the output from dialog, if any. Assumes a single text response.
#    if response['output']['generic']:
#        res2 = response['output']['generic'][0]['text']
	# esa es la respuesta escrita en el dialogo de la plataforma de watson
        #print(res) #esta se escribiria enseguida de la intencion detectada


    return 'set_slot {0} "{1}"'.format("watson",str(res))

def termina_watson():
# We're done, so we delete the session.
    service.delete_session(
        assistant_id = assistant_id,
        session_id = session_id
    )

