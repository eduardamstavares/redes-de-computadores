# O objetivo deste projeto eh implementar, na camada de aplicacao, um servico de entrega confiavel 
#de mensagens levemente baseado no TCP, com implementacao de pipelining. O programa a ser 
#desenvolvido recebera do servidor uma lista de musicas que poderao ser solicitadas atraves de um id, 
#e em seguida deve receber corretamente o arquivo a ser transferido do servidor. O servidor pode ser 
#acessado atraves do endereco IP 52.67.245.39. Na camada de transporte deve ser utilizado o protocolo UDP, 
#e a porta de destino deve ser a 50000. 
#Aluna: Maria Eduarda Silva Tavares, matricula: 20240008824
#Aluno: Lucas Franca de Melo Batista, matricula: 20240008243

import socket
import struct
import random
import sys

# Configuracoes do Servidor fornecidas na especificacao do projeto
IP_SERVIDOR = "52.67.245.39" #endereco de IP do servidor 
PORTA_SERVIDOR = 50000 #porta de destino 

# Requisicoes e Respostas (Cliente / Servidor)
CONN_REQ = 0x01 #criacao de conexao com servidor
CONN_ACK = 0x02 #confirmacao de criacao de conexao com cliente
MUSIC_SELECT = 0x03 #identificador da musica escolhida
MUSIC_RESPONSE = 0x04 #sequencia de mensagens com a musica 
MUSIC_RESPONSE_CONCLUDED = 0x05 #sinaliza fim do envio da musica e envia string de musicas pro cliente solicitar 
ACK = 0x06 # Confirmacao cumulativa enviada pelo cliente informando o proximo byte esperado
CONN_FIN = 0x07 #Solicitacao de encerramento da conexao enviada pelo cliente

# Mensagens Informativas / Erros do Servidor
TOO_SHORT_ERR = 0x08 #Mensagem do servidor informando que recebeu uma mensagem muito curta 
TOO_LONG_ERR = 0x09 #Mensagem do servidor informando que recebeu uma mensagem muito longa 
INVALID_CONN = 0x0A #Mensagem do servidor informando que recebeu uma mensagem com numero de conexao invalido 
INVALID_MUSIC = 0x0B #Mensagem informando escolha de musica invalida 
INVALID_MSG = 0x0C #Mensagem informando recebimento de numero de mensagem invalido 

# Funcao que cria a mensagem completa com o cabecalho de 7 bytes
def criar_cabecalho(tipo: int, num_msg: int, num_conexao: int, payload: bytes = b"") -> bytes: #retorno da funcao do tipo bytes
    cabecalho = struct.pack("<BIH", tipo, num_msg, num_conexao) #B: 1 byte, I: 4 bytes, H: 2 bytes, <:little-endian
    return cabecalho + payload #cabecalho + dados da mensagem

# Para ler/extrair os dados da mensagem recebida
def ler_cabecalho(mensagem: bytes): #mensagem recebida em bytes
    if len(mensagem) < 7: #mensagem precisa ter no minimo os 7 bytes do cabecalho caso nao tenha payload
        raise ValueError("Mensagem com tamanho inferior aos 7 bytes minimos.") #interrompe execucao da funcao 
    
    tipo, num_msg, num_conexao = struct.unpack("<BIH", mensagem[:7]) #pega os primeiros 7 bytes e converte para inteiros no formato especificado
    payload = mensagem[7:] #coloca os proximos 7 bytes da mensagem no payload, separando do cabecalho
    return tipo, num_msg, num_conexao, payload 
