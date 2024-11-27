#!/usr/bin/python3
"""
-------------------------------------------------
Nome do Arquivo: topdesk_notify_new_ticket.py
Descrição: Este script executa a verificação no Topdesk de novos tickets e envia os dados coletados via Webhook / Webflow com adaptivecards
Observações: Altere os campos que possuem "<!!!.." para que atenda aos seus requisitos. Referências da API em "https://developers.topdesk.com/"
Autor: Raphael Pereira
Data de Criação: 26/11/2024
Última Modificação: 27/11/2024
Versão: 1.0
-------------------------------------------------
"""
import requests, json, pymsteams, re, sys
from datetime import datetime, timezone, timedelta
from requests.auth import HTTPBasicAuth

def remove_warning(text,entryType):
    # Verificar qual foi o tipo de entrada do registro
    if (entryType == "Email"):
        # Regex de strings do começo do campo SE o ticket foi aberto via Email
        pattern_pre_subject = r'^[\s\S]*?\n\n(.*)'
        # Remover todo conteúdo antes do assunto
        text = re.sub(pattern_pre_subject, r'\1', text, flags=re.DOTALL)
    elif (entryType == "Telefone"):
        # Regex de strings do começo do campo SE o ticket foi aberto via Telefone/API
        pattern_pre_subject = r'^[^:]*:[^:]*:\s*(.*)'
        # Remover todo conteúdo antes da mensagem
        text = re.sub(pattern_pre_subject, r'\1', text, flags=re.DOTALL)
    # Regex de strings do final do email - Adicionar mais patterns de remoção SE NECESSÁRIO
    pattern_post_closing = r"Atenciosamente.*$||Cordialmente,.*$||Att.*$||ATT.*$||Regards.*$||A informação contida nesta mensagem é confidencial e privilegiada legalmente.*$||CUIDADO: Este e-mail foi originado de fora da organização.*$||This message is for the designated recipient only and may contain privileged, proprietary, or otherwise confidential information.*$||Abs,.*$||Esta mensagem pode conter informação confidencial e/ou privilegiada.*$"
    # Remover o conteúdo após os patterns
    text = re.sub(pattern_post_closing, '', text, flags=re.DOTALL)
    # Retorno do texto "limpo"
    return text

def sendwebhook(send_json,url_webhook):
    # Enviar dados via Webhook
    r = requests.post(url=url_webhook, json={ "type": "message", "attachments": [{ "contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": "null", "content": { "$schema": "http://adaptivecards.io/schemas/adaptive", "type": "AdaptiveCard", "version": "1.2", "body": [ { "type": "ColumnSet", "columns": [ { "type": "Column", "width": "stretch", "items": [ { "type": "TextBlock", "text": "Ticket: "+send_json["number"], "id": "acTicket", "spacing": "None", "horizontalAlignment": "Left", "size": "Large", "weight": "Bolder", "color": "Accent", "style": "heading", "fontType": "Default" } ] }, { "type": "Column", "width": "stretch", "items": [ { "type": "Image", "url": "https://liquipedia.net/commons/images/e/e7/TOPdesk_allmode.png", "size": "Large", "horizontalAlignment": "Right", "height": "25px", "selectAction": { "type": "Action.OpenUrl", "url": "https://<!!!SEU SUBDOMÍNIO AQUI!!!>.topdesk.net/tas/secure/login/form", "title": "Go to TopDesk" } } ] } ] }, { "type": "TextBlock", "text": send_json["callerBranch"]["name"] + " | " + send_json["briefDescription"], "weight": "Lighter", "size": "Large", "spacing": "Medium", "wrap": "true", "id": "acTitle", "separator": "true", "horizontalAlignment": "Center", "maxLines": 0, "isSubtle": "true", "fontType": "Default" }, { "type": "FactSet", "facts": [ { "title": "Status", "value": send_json["processingStatus"]["name"] }, { "title": "Solicitante", "value": send_json["caller"]["dynamicName"] }, { "title": "Operador", "value": send_json["operator"]["name"] }, { "title": "Data de Abertura", "value": send_json["creationDate"] }, { "title": "Vencimento em", "value": send_json["targetDate"] } ], "height": "stretch", "separator": "true" }, { "type": "TextBlock", "text": send_json["request"], "id": "acInstructions", "wrap": "true", "separator": "true" } ] } }] })
    print(r)

# Imprime na CLI os tickets
def printticket(item):
    print("Ticket:      ",item["number"])
    print("Abertura:    ",item['creationDate'])
    print("Vencimento:  ",item['targetDate'])
    print("Alteração:   ",item['modificationDate'])
    print("entryType:   ",item['entryType']['name'])
    print("Descrição:   ",item["briefDescription"])
    print("Solicitante: ",item["caller"]["dynamicName"])
    print("Empresa:     ",item["callerBranch"]["name"])
    print("Operador:    ",item["operator"]["name"])
    print("Time:        ",item["operatorGroup"]["name"])
    print("Status:      ",item["processingStatus"]["name"])
    print("Mensagem:    ",item["request"])
    print("------------------------")

#URL do novo Webhook
url_webhook = str(sys.argv[1])
# Credenciais do usuário
username = str(sys.argv[2])
password = str(sys.argv[3]) # API password
#ID dos grupos de operadores
idOperatorGroup = str(sys.argv[4])
# Tempo estipulado para visualizar os chamados modificados anteriores a X minutos
tempo_estipulado = int(sys.argv[5])
# Modo Verboso (ou não)
quiet = str(sys.argv[6])
# Data atual
current_dateTime = datetime.now(timezone.utc) #+ timedelta(minutes=10)
# Data atual menos X minutos
target_dateTime = current_dateTime - timedelta(minutes=tempo_estipulado)

#ID dos Status do TopDesk
idProcessingStatus = "<!!!IDs DOS STATUS DE PROCESSAMENTO SEPARADOS POR VÍRGULA!!!>"

# URL para fazer a requisição HTTP
url = "https://<!!!SEU SUBDOMÍNIO AQUI!!!>.topdesk.net/tas/api/incidents?query=operatorGroup.id=="+idOperatorGroup+";processingStatus.id=in=("+idProcessingStatus+")"

# Fazendo a requisição HTTP GET com autenticação básica para coletar os tickets
response = requests.get(url, auth=HTTPBasicAuth(username, password))

# Interpretando o conteúdo da resposta como JSON
if ( response.status_code != 204 and response.headers["content-type"].strip().startswith("application/json") and response.json is not None ):
    response_json = response.json()
elif ( response.status_code < 400 ):
    print(f'Nenhum chamado novo encontrado. Saindo...\nStatus: {response.status_code}')
    sys.exit(0)
else:
    print(f'Erro {response.status_code}')
    sys.exit(2)
# Numero de tickets que exedem o tempo
n=0
# Numero total de tickets lidos com a requisição HTTP GET
y=0

# Loop para verificar Ticket a Ticket se ele atende o requisito de tempo de modificação
for item in response_json:
    y+=1
    # Mudar o tipo de variável para Datatime (para efetuar a comparação de tempo)
    item['modificationDate'] = datetime.strptime(item['modificationDate'], '%Y-%m-%dT%H:%M:%S.%f%z')
    # Muda o tipo da variável para string já formatada de data 'dd/mm/aa h:m' - OBS.: Redução de 3 horas devido ao TimeZone, mude para seu timezone!!!
    item['creationDate'] = (datetime.strptime(item['creationDate'], '%Y-%m-%dT%H:%M:%S.%f%z') - timedelta(hours=3)).strftime('%d/%m/%Y %H:%M')
    item['targetDate'] = (datetime.strptime(item['targetDate'], '%Y-%m-%dT%H:%M:%S.%f%z') - timedelta(hours=3)).strftime('%d/%m/%Y %H:%M')
    # Efetuar a comparação de tempo entre o tempo alvo e a última alteração do chamado
    if target_dateTime < item['modificationDate']:
        # Mudar o tipo da variável para string já formatada
        item['modificationDate'] = (item['modificationDate'] - timedelta(hours=3)).strftime('%d/%m/%Y %H:%M')
        # Remove strings desnecessárias do código
        item["request"] = remove_warning(item["request"],item['entryType']['name'])
        # Reduz a quantidade de caracteres da string (para evitar um Webhook gigante)
        item["request"] = (item["request"][:1200] + '..') if len(item["request"]) > 1200 else item["request"]
        # Apresentar dados na CLI
        if (quiet == "False"):
            printticket(item)
        # Enviar dados para o Webhook
        sendwebhook(item,url_webhook)
    else:
        n+=1
if (quiet == "False"):
    # Se não encontrou chamados que atendem ao requisito de tempo de modificação
    if (y == n):
        print(f'Nenhum chamado dentro do tempo estipulado ({tempo_estipulado} minutos)')
        sys.exit(0)
    # Se encontrou chamados que atendem ao requisito de tempo de modificação
    else:
        print(f'Do(s) {y} chamado(s) observado(s), {n} não estava(m) dentro do tempo estipulado ({tempo_estipulado} minutos)')
        sys.exit(0)