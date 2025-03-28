from monsterui.all import *
from fasthtml.common import *

save_script = Script("""
function saveTableToLocalStorage() {
    // Get syndrome from the page title instead of the input field
    let titleElement = document.querySelector("h2");
    let titleText = titleElement ? titleElement.textContent : "";
    let syndrome = titleText.replace("Studying: ", "").trim();
    
    let tableData = {syndrome: syndrome, conditions: [], cells: {}};
    
    const headerCells = document.querySelectorAll('thead th');
    for (let i = 1; i < headerCells.length; i++) {
        tableData.conditions.push(headerCells[i].textContent.trim());
    }
    
    const textareas = document.querySelectorAll('textarea[id^="cond"]');
    textareas.forEach(textarea => {
        tableData.cells[textarea.id] = textarea.value;
    });
    
    localStorage.setItem("verticalReadingData", JSON.stringify(tableData));
    console.log("Table data saved to localStorage");
    return true;
}

function tableToCSV(data) {
    const aspects = ["Epidemiology", "Time Course", "Symptoms and Signs", "Mechanisms of Disease"];
    const {syndrome, conditions, cells} = data;

    const header = ["Aspect", ...conditions].join(',');

    function makeRow(aspect) {
        const values = conditions.map((_, i) => {
            const value = cells[`cond${i}_${aspect}`] || "";
            return `"${value.replace(/"/g, '""')}"`;
        });
        return [aspect, ...values].join(',');
    }
    
    const rows = aspects.map(makeRow);
    return [header, ...rows].join('\\n');
}

function downloadCSV(csvData, filename) {
    // Create a blob with the CSV data
    const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
    
    // Create a URL for the blob
    const url = URL.createObjectURL(blob);
    
    // Create a link element to trigger the download
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    
    // Append to document, click, and clean up
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function downloadTableAsCSV() {
    // First make sure data is saved
    saveTableToLocalStorage();

    const savedData = JSON.parse(localStorage.getItem("verticalReadingData"));
    if (!savedData) {
        alert("No data found to download");
        return;
    }
    
    const csvData = tableToCSV(savedData);
    const filename = `${savedData.syndrome}_table.csv`;
    downloadCSV(csvData, filename);
}

function compareWithAI() {
    saveTableToLocalStorage();
                     
    const savedData = JSON.parse(localStorage.getItem("verticalReadingData"));
    if (!savedData) {
        alert("Please save your table first before comparing with AI");
        return;
    }
    
    const syndrome = savedData.syndrome;
    const conditions = savedData.conditions;
    
    let url = `/research?aspect=full_comparison&syndrome=${encodeURIComponent(syndrome)}`;
    conditions.forEach((condition, i) => {
        url += `&condition${i+1}=${encodeURIComponent(condition)}`;
    });
    
    // Trigger HTMX request manually
    htmx.ajax('GET', url, {target: '#ai-feed-area', swap: 'innerHTML'});
}

                                          
// Use HTMX's event system instead of DOMContentLoaded
document.body.addEventListener('htmx:afterSwap', function() {
    document.querySelectorAll('textarea[id^="cond"]').forEach(textarea => {
        textarea.addEventListener('input', saveTableToLocalStorage);
    });
});

// Add functions to the global scope to make them available for onclick
window.saveTableToLocalStorage = saveTableToLocalStorage;
window.downloadTableAsCSV = downloadTableAsCSV;
window.compareWithAI = compareWithAI;
""")





import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

from google import genai
MODEL = 'gemini-2.0-flash-exp'
client = genai.Client(api_key=api_key)

hdrs = (Theme.violet.headers(), MarkdownJS())

app, rt = fast_app(live=True, debug=True, hdrs=hdrs)

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
                                 hx_target='#ai-feed-area', hx_swap='innerHTML', hx_indicator='#research-loading'),
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
    Button("Save", cls=ButtonT.secondary, onclick="saveTableToLocalStorage();alert('Table saved successfully!');"),
    Button("Download CSV", cls=ButtonT.primary, onclick="downloadTableAsCSV()"),
    Button('Compare with AI', cls=ButtonT.secondary, onclick="compareWithAI()"),
    cls="flex space-x-4 justify-center mt-4"
)


def query_google_ai(prompt):
    try:
        search_tool = {'google_search':{}}
        chat = client.chats.create(model=MODEL, config={'tools':[search_tool]})
        response = chat.send_message(prompt)
        result = ''.join([part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')]) # Combine all text parts from the response
        return Div(Safe(result))
    except Exception as e:
        return P(f"Error querying AI: {str(e)}", cls="text-red-500")


def create_prompts(syndrome, conditions):
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


def create_comparison_prompt(syndrome, conditions):    
    return f"""Create a comprehensive comparison table for {syndrome} caused by these conditions: {", ".join(conditions)}.

For each condition, analyze and compare these aspects:
1. Epidemiology: Who gets it? Include demographics, risk factors, prevalence, and incidence.
2. Time Course: How does it present and evolve? Include onset characteristics, progression pattern, duration, and resolution.
3. Symptoms and Signs: What are the clinical manifestations? 
4. Mechanisms of Disease: What is the pathophysiology? Include causal mechanisms.

After describing each aspect for all conditions, identify:
- COMMON features present in all conditions
- DIFFERENTIATING features present in only two conditions (specify which two)
- KEY features unique to only one condition (specify which one)

Format your response as a clear, well-structured markdown table that medical students can easily study from."""


def research_conditions(syndrome, conditions, aspect):
    if aspect == "full_comparison": return query_google_ai(create_comparison_prompt(syndrome, conditions))
    
    prompts = create_prompts(syndrome, conditions)
    prompt = prompts.get(aspect)
    if not prompt: return Div(P(f"Unknown research aspect: {aspect}"), cls="p-4 bg-red-100")
    return query_google_ai(prompt)

@rt('/research')
def research(request):
    aspect = request.query_params.get('aspect')
    syndrome = request.query_params.get('syndrome')

    i, conditions = 1, []
    while f'condition{i}' in request.query_params:
        condition = request.query_params.get(f'condition{i}')
        if condition: conditions.append(condition)
        i += 1    
    
    if not aspect or not syndrome or not conditions:
        return Div(P("Missing required parameters"), cls="p-4 bg-red-100")
    results = research_conditions(syndrome, conditions, aspect)
    return Div(
        H3(f"Research: {aspect} for {syndrome}\n\n", cls="text-xl font-bold mb-4"),
        results,
        cls="p-4 marked"
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
        Div(
            A(DivLAligned(UkIcon('home', cls='mr-2'), "Home"), 
              href='/', 
              cls='text-primary hover:underline mb-4'),
            cls='flex flex-col'
        ),
        H2(f"Studying: {syndrome}", cls="text-xl mb-4"),
        table,
        Div(Loading(cls=LoadingT.spinner + " h-8 w-8"),
            cls="htmx-indicator flex justify-center my-4", id="research-loading"),
        buttons,
        save_script,
        Div(id="ai-feed-area", cls="mt-6 p-4 border rounded-md min-h-[200px]"),
        cls="py-4"
    )

@rt('/')
def index():
    return Container(Div(id='main-content', cls='py-8') (input_form))

serve()