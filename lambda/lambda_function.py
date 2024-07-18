import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.dispatch_components import AbstractRequestInterceptor
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from openai import OpenAI
import requests
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = OpenAI(
        api_key=""
)

api_url = ""

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = "Bienvenido al asistente, ¿cómo puedo ayudarte hoy?"

        session_attr = handler_input.attributes_manager.session_attributes
        session_attr["chat_history"] = []

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class GptQueryIntentHandler(AbstractRequestHandler):
    """Handler for Gpt Query Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("GptQueryIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        query = handler_input.request_envelope.request.intent.slots["query"].value

        session_attr = handler_input.attributes_manager.session_attributes
        chat_history = session_attr["chat_history"]
        response = generate_gpt_response(chat_history, query)
        session_attr["chat_history"].append((query, response))

        return (
                handler_input.response_builder
                    .speak(response)
                    .ask("¿Tienes otra consulta?")
                    .response
            )

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors."""
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Lo siento, no entendi lo que dijiste. Puedes repetirlo?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class InitSurveyIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("InitSurveyIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "¿Qué tan satisfecho estás con la asistencia? Por favor, califica del 1 al 5."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class SatisfactionRatingIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("SatisfactionRatingIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        rating = slots["rating"].value
        requests.post(api_url + "rate/?rating=" + rating)

        if rating == "1":
            speak_output = f"Has calificado con {rating} estrella. Estamos trabajando para mejorar nuestro servicio. ¡Gracias por tu retroalimentación!"
        elif rating == "2":
            speak_output = f"Has calificado con {rating} estrellas. Estamos trabajando para mejorar nuestro servicio. ¡Gracias por tu retroalimentación!"
        elif rating == "3" or rating == "4":
            speak_output = f"Has calificado con {rating} estrellas. ¡Gracias por tu retroalimentación!"
        elif rating == "5":
            speak_output = f"Has calificado con {rating} estrellas. ¡La mejor calificación! ¡Gracias por tu retroalimentación!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Handler for AMAZON.CancelIntent and AMAZON.StopIntent."""
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # Respuesta de Alexa
        speak_output = "¡Gracias por usar nuestro servicio!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


def generate_gpt_response(chat_history, new_question):
    try:
        messages = [{"role": "system", "content": "You are a helpful assistant, you have a conversation with a human who are trying to solve his doubts of Tecsup, use the documents to answer the question and don't mention them in the conversation, Answer as briefly and simply as possible, if you don't find the answer in the documents or the documents have information who is not useful or not have relation with the question, just say that you don't know the answer like this: 'Lo siento, no tengo la información para responder esa pregunta. ¿Te puedo ayudar con otra consulta?'"}]
        for question, answer in chat_history[-4:]:
            messages.append({"role": "user", "content": question})
            messages.append({"role": "assistant", "content": answer})
        
        api = api_url + new_question.replace(" ", "_") + "?"
        docs = requests.get(api).json()

        messages.append({"role": "assistant", "content": "I found this documents use to aswer the question, if you don't find the answer in the documents or documents are empty, dont try to answer it, just say that you don't know the answer like this: 'Lo siento, no tengo la información para responder esa pregunta. ¿Te puedo ayudar con otra consulta?': {}".format(json.dumps(docs))})
        
        messages.append({"role": "user", "content": new_question})
        print(docs)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            max_tokens=140,
            n=1,
            temperature=0.6
        )
        if response.choices[0].message.content == "Lo siento, no tengo la información para responder esa pregunta. ¿Te puedo ayudar con otra consulta?":
            requests.post(api_url + "insert_question_nr/?question=" + new_question.replace(" ", "_"))

        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return f"Error generating response: {str(e)}"

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GptQueryIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_exception_handler(CatchAllExceptionHandler())
sb.add_request_handler(SatisfactionRatingIntentHandler())
sb.add_request_handler(InitSurveyIntentHandler())

lambda_handler = sb.lambda_handler()
