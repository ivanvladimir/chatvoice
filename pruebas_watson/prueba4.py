# Example 3: Implements app actions.

import watson_developer_cloud
import time

# Set up Assistant service.
service = watson_developer_cloud.AssistantV2(
    iam_apikey = 'Bufv_wnpCVf3XuuEi6bg44JBsEZyjs9zkxl0vIk04bY3', # replace with API key
    version = '2018-09-20'
)

assistant_id = '456d6ce8-901c-4b8f-a91f-82382a63d2c6' # replace with assistant ID

# Create session.
session_id = service.create_session(
    assistant_id = assistant_id
).get_result()['session_id']

# Initialize with empty values to start the conversation.
user_input = ''
current_action = ''

# Main input/output loop
while current_action != 'end_conversation':
    # Clear any action flag set by the previous response.
    current_action = ''

    # Send message to assistant.
    response=service.message(
        assistant_id='{assistant_id}',
        session_id='{session_id}',
        input={
            'message_type': 'text',
            'text': 'Hello',
            'options': {
                'return_context': True
            }
        },
        context={
            'global': {
                'system': {
                    'user_id': 'my_user_id'
                }
            },
            'skills': {
                'main skill': {
                    'user_defined': {
                        'account_number': '123456'
                    }
                }
            }
        }
    ).get_result()

    print(json.dumps(response, indent=2))


    # Print the output from dialog, if any. Assumes a single text response.
    if response['output']['generic']:
        print(response['output']['generic'][0]['text'])

    # Check for client actions requested by the assistant.
    if 'actions' in response['output']:
        if response['output']['actions'][0]['type'] == 'client':
            current_action = response['output']['actions'][0]['name']

    # User asked what time it is, so we output the local system time.
    if current_action == 'display_time':
        print('The current time is ' + time.strftime('%I:%M:%S %p') + '.')
    # If we're not done, prompt for next round of input.
    if current_action != 'end_conversation':
        user_input = input('>> ')

# We're done, so we delete the session.
service.delete_session(
    assistant_id = assistant_id,
    session_id = session_id
)

