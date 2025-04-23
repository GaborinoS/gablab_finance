from flask import Blueprint, render_template

main = Blueprint('main', __name__)

@main.route('/')
def home():
    modules = [
        {
            'name': 'Zeitreihen',
            'description': 'Analysieren Sie Finanzdaten im Zeitverlauf',
            'url': '/timeseries',
            'icon': 'chart-line'
        },
        {
            'name': 'Kosten/Einkommen Visu',
            'description': 'Visualisieren Sie Ihre Einnahmen und Ausgaben',
            'url': '/costincome',
            'icon': 'chart-pie'
        }
    ]
    return render_template('home.html', modules=modules)