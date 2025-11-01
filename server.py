import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, callback_context, Input, Output
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

# load data
df = pd.read_feather("2025_KV_Lasse_data.feather").reset_index()
df.columns = df.columns.str.replace(".0", "")  # fix lige lidt med DR sprg id

color_dict = pd.read_json("various.json").apply(lambda x: x.str.lower()).set_index('bogstav_leg')['farver'].to_dict()
bogfarve = pd.read_json("various.json").reset_index()
bogfarve['bogstav_leg'] = bogfarve['bogstav_leg'].str.lower()
bogfarve = bogfarve.set_index('bogstav_leg')

# hjælp til farveblinde
df['bogstav'] = df.parti.map(bogfarve['index']).fillna('X')
df['sized'] = 5

tv2_sprg = pd.read_json('TV2/tv2_sprg.json').set_index('id')['question']
#dr_sprgs = pd.read_json('dr1_sprg.json')
dr_sprgs = pd.Series({
    "DR0": "Flere penge til uddannelse, skoler og børnehaver",
    "DR1": "Mere privatisering",
    "DR2": "Tage hensyn og bruge flere penge på sociale mindretal",
    "DR3": "Tage hensyn og bruge flere penge på religiøse mindretal",
    "DR4": "Bedre forhold for privat trafik ",
    "DR5": "Der skal generelt bruges flere penge på velfærd",
    "DR6": "Erhverslivet skal hjælpes",
    "DR7": "Flere grønne tiltag",
    "DR8": "Mere brugerbetaling",
    "DR9": "Mere fokus på integration",
    "DR10": "Flere boliger og lejeboliger",
    "DR11": "Flere penge på idræt og kultur",
    "DR12": "Flere penge til små samfund/landsbyer/skoler",
    "DR13": "Mere offentligt indblik i kommunens aktiviteter",
    "DR14": "Kommunen skal gøre mere for at sikre borgerne mod klimaforandringerne",
    "DR15": "Flere penge til de ældre",
    "DR16": "Der skal satses mere på turisme",
    "DR17": "Bedre offentlig transport",
    "DR18": "Prioriter natur over erhverv",
    "DR19": "Mere politi og kontrol med at regler overholdes",
})

# liste over columns med spørgsmål
dk_spg_columns = list(df.columns[df.columns.str.startswith("DR") | df.columns.str.startswith("tv2")])
#dr_sprgs.columns = dr_sprgs.columns.str.lower()
sprgs = pd.concat([tv2_sprg, dr_sprgs])#[['id', 'question']].set_index('id')
#sprgs.index = sprgs.index.astype('str')
sprgs = sprgs.loc[dk_spg_columns]
svar_muligheder = ['helt uenig', 'uenig', 'neutral', 'enig', 'helt enig']


def do_calcs(kreds = None):
    if kreds is None or 'alle' in kreds:
        a = df
    else:
        a = df[df.kreds.isin(kreds)]

    # do calcs
    X = a[dk_spg_columns]
    y = a['parti']
    lda = LinearDiscriminantAnalysis(n_components=2).fit(X, y)
    return lda, pd.concat([a, pd.DataFrame(lda.transform(a[dk_spg_columns]), columns=["X", "y"]).set_index(a.index)], axis=1)

def confidence_ellipse(xs, ys, n_std=1.96, size=100):
    cov = np.cov(xs, ys)
    pearson = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    theta = np.linspace(0, 2 * np.pi, size)
    ellipse_coords = np.column_stack([ell_radius_x * np.cos(theta), ell_radius_y * np.sin(theta)])
    x_scale = np.sqrt(cov[0, 0]) * n_std
    x_mean = np.mean(xs)
    y_scale = np.sqrt(cov[1, 1]) * n_std
    y_mean = np.mean(ys)
    translation_matrix = np.tile([x_mean, y_mean], (ellipse_coords.shape[0], 1))
    rotation_matrix = np.array([[np.cos(np.pi / 4), np.sin(np.pi / 4)], [-np.sin(np.pi / 4), np.cos(np.pi / 4)]])
    scale_matrix = np.array([[x_scale, 0], [0, y_scale]])
    ellipse_coords = ellipse_coords.dot(rotation_matrix).dot(scale_matrix) + translation_matrix

    path = f'M {ellipse_coords[0, 0]}, {ellipse_coords[0, 1]}'
    for k in range(1, len(ellipse_coords)):
        path += f'L{ellipse_coords[k, 0]}, {ellipse_coords[k, 1]}'
    path += ' Z'
    return path

app = Dash(
	title="Kommunalvalg 2025 - DumData analyse",
	external_stylesheets=[dbc.themes.SOLAR, dbc.icons.BOOTSTRAP],
	meta_tags=[{"name": "viewport", "content": "initial-scale=1"}, ],
)
server = app.server

app.layout = dbc.Container([
	dcc.Store(id='bruger_coord'),
	dbc.Card(
		dbc.Container(
			[
				html.H2("Kommunalvalg 2025"),
				html.P("Analyse af hvor de enkelte kandidater står i forhold til hinanden og deres partier",
					   className="lead", ),
			],  # fluid=True,
		), body=True
	),
	dbc.Card(
		[
			dbc.Card([
                # opdater til dbc ting
                html.Label(["kreds filter:", dcc.Dropdown(id='kreds_valg', options=[{'value':'alle', 'label':'alle'}, *[{'value': x, 'label': x} for x in df.kreds.unique()]], value=['alle',], multi=True)]),
				dbc.Switch(id='parti_shadow', value=False, label="Tegn cirkler om partierne"),
				dbc.Switch(id='farveblind', value=False, label="Farveblind mode"),
			], body=True)
		],
	),

	dbc.Card(dcc.Graph(id='viz')),
	dbc.Card(html.P("(her kommer forudsigelser om hvilket parti en 'klikket' politiker burde være i)", id="svar_res")),
	dbc.Card([
		dcc.Markdown('''
		# SVAR
		### Tryk på politiker for at se deres svar eller svar selv for at se hvor DU ligger
		helt uenig  --  uenig  --  neutral  --  enig  --  helt enig
		'''),
		dbc.ListGroup([
			dbc.ListGroupItem([
				html.P(sprgs.loc[spg]),
				dcc.RadioItems(id=spg, options=[{'label': '', 'value': x / 4} for x in range(5)],
							   value=0, labelStyle={'display': 'inline-block'})
			]) for spg in dk_spg_columns
		], flush=True)
	], body=True)
	, ],  # fluid=True
)


# %%
@app.callback(Output('viz', 'figure'),
    Input('kreds_valg', 'value'),
    Input('parti_shadow', 'value'),
    Input('farveblind', 'value'),
    Input('bruger_coord', 'data'))
def update_graph(valgkreds_filter, shadow, farveblind, data):
    lda, a = do_calcs(valgkreds_filter)

    if farveblind:
        f1 = px.scatter(
            a, x='X', y='y', color='parti', color_discrete_map=color_dict, hover_data=['navn', 'job', 'alder'],
            custom_data=['index'], template="plotly_dark", labels={"X": "Hjalmesans", "y": "Fluplighed"},
            size='sized', text='bogstav', size_max=15
            # , width=1000  # , marginal_x='box'
        )
    else:
        f1 = px.scatter(
            a, x='X', y='y', color='parti', color_discrete_map=color_dict, hover_data=['navn', 'job', 'alder'],
            custom_data=['index'], template="plotly_dark", labels={"X": "Hjalmesans", "y": "Fluplighed"}
        )
        if 'alle' in valgkreds_filter:
            f1.update_traces(marker=dict(size=3))


    f1.layout.xaxis.fixedrange = True
    f1.layout.yaxis.fixedrange = True
    f1.update_layout(modebar_remove=['zoom', 'pan', 'select', 'lasso2d'])

    if shadow:
        for ii, (i, pari_data) in enumerate(a.groupby('parti')):
            if len(pari_data.X) > 2:
                f1.add_shape(type='path', path=confidence_ellipse(pari_data.X, pari_data.y),
                             line_color='rgb(255,255,255,1)', fillcolor=color_dict[i] if i in color_dict else 'rgb(255,255,255,0.2)', opacity=.4, )
    if data['dine_aktiv']:
        # f1.add_scatter(x=[data['dine_coords'][0]], y=[data['dine_coords'][1]], mode='markers', marker_symbol='star', marker_size=15)
        f1.add_vline(data['dine_coords'][0], line_dash="dash", line_color="pink")
        f1.add_hline(data['dine_coords'][1], line_dash="dash", line_color="pink")
    return f1


@app.callback(
        *[Output(x, 'value') for x in dk_spg_columns],
        Output('svar_res', 'children'),
        Output('bruger_coord', 'data'),
    {
        'valgkreds_filter': Input('kreds_valg', 'value'),
        'clickData': Input('viz', 'clickData'),
        'spg_in': [Input(x, 'value') for x in dk_spg_columns]
    })
def display_click_data(valgkreds_filter, clickData, spg_in):
    lda, a = do_calcs(valgkreds_filter)

    ctx = callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger_id == 'viz':
        dine_aktiv = False
        if clickData and len(clickData['points']) != 0:
            idx = clickData['points'][0]['customdata'][0]
            navn = clickData['points'][0]['customdata'][1]
        else:
            idx = 1350
            navn = "(klik på nogen)"
        row = a[a['index'] == idx]
        parti = row['parti'].iloc[0]
        nyt_parti = lda.predict(row[dk_spg_columns])[0]
        return [*[row[x].iloc[0] for x in dk_spg_columns],
                f"Du har klikket på {navn}, {parti}. Vedkomne burde overveje {nyt_parti}",
                {'dine_aktiv': dine_aktiv, 'dine_coords': [0, 0]}]
    else:
        dine_aktiv = True
        a = pd.DataFrame(spg_in, index=dk_spg_columns).T
        dine_coords = lda.transform(a)[0]
        return [*[x for x in spg_in],
                f"Dine koordinater er {dine_coords[0]:.1f}, {dine_coords[1]:.1f}. Du burde overveje {lda.predict(a)[0]}",
                {'dine_aktiv': dine_aktiv, 'dine_coords': dine_coords}]


if __name__ == "__main__":
    app.run(port=9000)
# app.run_server(debug=True)
