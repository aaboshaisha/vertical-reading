from monsterui.all import *
from fasthtml.common import *

import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

from google import genai


hdrs = (Theme.violet.headers(), MarkdownJS())

app, rt = fast_app(live=True, hdrs=hdrs)

input_form = Card(
    CardHeader(H2("Vertical Reading Tool", cls='text-center')),
    CardBody(
        Form(
            LabelInput("Syndrome", id="syndrome", placeholder="e.g., Pharyngitis"),
            Div(H4("Conditions that cause this syndrome:"), cls="mt-4 mb-2"),
            LabelInput("Condition 1", id="condition1", placeholder="e.g., Group A beta hemolytic strep"),
            LabelInput("Condition 2", id="condition2", placeholder="e.g., Infectious mononucleosis"),
            LabelInput("Condition 3", id="condition3", placeholder="e.g., Acute retroviral syndrome"),
            Div(Button("Start Study", cls=ButtonT.primary), cls='flex justify-center mt-4'),
            cls='space-y-4',
            hx_post='/create-study',
            hx_target='#main-content',
            hx_swap='innerHTML'
        )
    ),
    cls="max-w-2xl mx-auto"
)

rownames = ["Epidemiology", "Time Course", "Symptoms and Signs", "Mechanisms of Disease"]

def create_header(colnames):
    return Thead(Tr(Th('Aspect'), *[Th(colname) for colname in colnames]))

def create_table(table_header, ncols=3, syndrome='', conditions=None):
    rows = []
    for i, rowname in enumerate(rownames):
        aspect_cell = Div(rowname,
                          Button("Research", cls=ButtonT.secondary + " text-xs mt-2",
                                 hx_get=f"/research?aspect={urllib.parse.quote(rowname)}&syndrome={urllib.parse.quote(syndrome)}" + "".join([f"&condition{j+1}={urllib.parse.quote(c)}" for j, c in enumerate(conditions or [])]),
                                 hx_target='#ai-feed-area', hx_swap='innerHTML'),
                          cls="flex flex-col items-start")
        
        row = Tr(
            Th(aspect_cell, cls="align-top p-2 border border-slate-300"),
            *[Td(TextArea(rows=2, id=f'cond{i}_{rowname}', placeholder='Enter your text here...', 
                         cls='w-full border-0 resize-none'), 
                cls="p-0 border border-slate-300") for i in range(ncols)]
        )
        rows.append(row)
    return Table(table_header, Tbody(*rows), cls="w-full border-collapse border border-slate-300")

buttons = Div(
    Button('AI Complete Table', cls=ButtonT.primary),
    Button('Compare with AI', cls=ButtonT.secondary),
    cls="flex space-x-4 justify-center mt-4"
)

MODEL = 'gemini-2.0-flash-exp'
client = genai.Client(api_key=api_key)

def query_google_ai(prompt):
    try:
        search_tool = {'google_search':{}}
        chat = client.chats.create(model=MODEL, config={'tools':[search_tool]})
        response = chat.send_message(prompt)
        result = response.candidates[0].content.parts[0].text
        return Div(Safe(result), cls='markdown')
    except Exception as e:
        return P(f"Error querying AI: {str(e)}", cls="text-red-500")

def create_prompts(syndrome, conditions):
    """Create prompts dictionary based on syndrome and conditions."""
    return {
        "Epidemiology": f"What is the epidemiology (who gets it, risk factors, prevalence, age groups) of each of these conditions that cause {syndrome}: {', '.join(conditions)}? For each condition, provide a concise, factual summary.",
        
        "Time Course": f"What is the temporal course/pattern (how it presents and evolves over time) of each of these conditions that cause {syndrome}: {', '.join(conditions)}? Include onset, progression, duration, and resolution for each condition.",
        
        "Symptoms and Signs": f"""What are the symptoms and signs of each of these conditions that cause {syndrome}: {', '.join(conditions)}?
        After listing them for each condition, organize them into:
        1. COMMON Features: present in all conditions
        2. DIFFERENTIATING Features: present in only two conditions (specify which two)
        3. KEY Features: present in only one condition (specify which one)""",
        
        "Mechanisms of Disease": f"What are the mechanisms by which each of these conditions causes {syndrome}: {', '.join(conditions)}? Explain the pathophysiology in clear, concise terms for each condition."
    }

def research_conditions(syndrome, conditions, aspect):
    prompts = create_prompts(syndrome, conditions)
    prompt = prompts.get(aspect)
    if not prompt:
        return Div(P(f"Unknown research aspect: {aspect}"), cls="p-4 bg-red-100")
    results = query_google_ai(prompt)
    
    return Div(
        H3(f"{aspect} Research", cls="text-lg font-bold mb-2"),
        P(f"Research results for {', '.join(conditions)}", cls="italic mb-4"),
        Div(results, cls="p-4 bg-slate-50 rounded"),
        cls="p-4 border rounded-md"
    )


@rt('/research')
def research(request):
    aspect = request.query_params.get('aspect')
    syndrome = request.query_params.get('syndrome')

    i, conditions = 1, []
    while f'condition{i}' in request.query_params:
        condition = request.query_params.get(f'condition{i}')
        if condition:
            conditions.append(condition)
        i += 1    
    
    if not aspect or not syndrome or not conditions:
        return Div(P("Missing required parameters"), cls="p-4 bg-red-100")
    results = research_conditions(syndrome, conditions, aspect)
    return Div(
        H3(f"Research: {aspect} for {syndrome}", cls="text-xl font-bold mb-4"),
        results,
        cls="p-4 border rounded-md marked"
    )

@rt('/create-study')
async def post(request):
    form = await request.form()
    syndrome = form.get('syndrome')
    conditions = [form.get('condition1'), form.get('condition2'), form.get('condition3')]
    conditions = [c for c in conditions if c] # filter empty vals
    if not syndrome or len(conditions) < 2:
        return Alert("Please enter a syndrome and at least 2 conditions", cls=AlertT.error)
    
    table = create_table(table_header=create_header(conditions), ncols=len(conditions), syndrome=syndrome, conditions=conditions)

    return Div(
        H2(f"Studying: {syndrome}", cls="text-xl mb-4"),
        table,
        buttons,
        Div(id="ai-feed-area", cls="mt-6 p-4 border rounded-md min-h-[200px]"),
        cls="py-4"
    )

@rt('/')
def index():
    return Container(Div(id='main-content', cls='py-8') (input_form))

serve()