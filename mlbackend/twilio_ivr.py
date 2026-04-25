from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse
from .llm_service import get_llm_response

router = APIRouter()

@router.post("/api/ivr/incoming")
async def ivr_incoming(request: Request):
    """
    Called by Twilio when a farmer dials the AgriSaathi phone number.
    It greets them and prompts them to ask a question.
    """
    resp = VoiceResponse()
    
    # We use Gather to capture user speech
    gather = resp.gather(
        input='speech',
        action='/api/ivr/process',
        timeout=5,
        language='hi-IN' # Default to Hindi for Indian farmers, or en-IN
    )
    
    # The greeting text
    greeting = "Welcome to AgriSaathi. Please speak your farming question after the beep."
    gather.say(greeting, language='hi-IN')
    
    # Fallback if they stay silent
    resp.say("We didn't receive any input. Goodbye.", language='hi-IN')
    
    return HTMLResponse(content=str(resp), media_type="application/xml")

@router.post("/api/ivr/process")
async def ivr_process(request: Request, SpeechResult: str = Form(None)):
    """
    Called by Twilio when the user finishes speaking.
    SpeechResult contains the transcribed text.
    """
    resp = VoiceResponse()
    
    if not SpeechResult:
        resp.say("Sorry, I could not hear you. Please try calling again.", language='hi-IN')
        return HTMLResponse(content=str(resp), media_type="application/xml")
    
    # Ask the LLM to get an answer to the farmer's spoken question
    prompt = f"A farmer called on the phone and asked: {SpeechResult}. Answer them concisely in a few sentences."
    system_instruction = "You are an expert agriculture assistant in India. Give short, direct answers suitable for reading out loud over a phone call."
    
    ai_answer = get_llm_response(prompt=prompt, system_prompt=system_instruction)
    
    # Speak the answer back to the user
    resp.say(ai_answer, language='hi-IN')
    
    # Hang up
    resp.hangup()
    
    return HTMLResponse(content=str(resp), media_type="application/xml")
