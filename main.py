from monsterui.all import *
from fasthtml.common import *

hdrs = Theme.blue.headers()
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

def create_table(table_header, ncols=3):
    rows = []
    for rowname in rownames:
        aspect_cell = Div(rowname,Button("Research", cls=ButtonT.secondary + " text-xs mt-2"),
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

@rt('/create-study')
async def post(request):
    form = await request.form()
    syndrome = form.get('syndrome')
    conditions = [form.get('condition1'), form.get('condition2'), form.get('condition3')]
    conditions = [c for c in conditions if c] # filter empty vals
    if not syndrome or len(conditions) < 2:
        return Alert("Please enter a syndrome and at least 2 conditions", cls=AlertT.error)
    
    table = create_table(table_header=create_header(conditions), ncols=len(conditions))

    return Div(
        H2(f"Studying: {syndrome}", cls="text-xl mb-4"),
        table,
        Div(id="ai-feed-area", cls="mt-6 p-4 border rounded-md min-h-[200px] hidden"),
        buttons,
        cls="py-4"
    )

@rt('/')
def index():
    return Container(Div(id='main-content', cls='py-8') (input_form))

serve()