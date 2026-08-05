""" 
O objetivo deste projeto eh implementar, na camada de aplicacao, um servico de entrega confiavel 
de mensagens levemente baseado no TCP, com implementacao de pipelining. O programa a ser 
desenvolvido recebera do servidor uma lista de musicas que poderao ser solicitadas atraves de um id, 
e em seguida deve receber corretamente o arquivo a ser transferido do servidor. O servidor pode ser 
acessado atraves do endereco IP 52.67.245.39. Na camada de transporte deve ser utilizado o protocolo UDP, 
e a porta de destino deve ser a 50000. 
"""
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
    """ 
        cabecalho em little-endian de 7 bytes (<BIH):
        tipo = 1 byte (B)
        num_msg = 4 bytes (I)
        num_conexao = 2 bytes (H)
        depois juntará com os dados extras do payload
    """
    return cabecalho + payload #cabecalho + dados da mensagem

# Para ler/extrair os dados da mensagem recebida
def ler_cabecalho(mensagem: bytes): #mensagem recebida em bytes
    if len(mensagem) < 7: #mensagem precisa ter no minimo os 7 bytes do cabecalho caso nao tenha payload
        raise ValueError("Mensagem com tamanho inferior aos 7 bytes minimos.") #interrompe execucao da funcao 
    
    tipo, num_msg, num_conexao = struct.unpack("<BIH", mensagem[:7]) #pega os primeiros 7 bytes e converte para inteiros no formato especificado
    payload = mensagem[7:] #coloca os proximos 7 bytes da mensagem no payload, separando do cabecalho
    return tipo, num_msg, num_conexao, payload 

#funcao responsavel por iniciar a conexao do cliente e servidor
def iniciar_conexao(meu_socket):
    """
    Faz o handshake inicial com o servidor (CONN_REQ).
    Gera o número de sequência inicial e recebe o ID da conexão + Menu.
    """
    # Gera um número aleatório para começar a contar os bytes
    byte_inicial = random.randint(1, 1000000)
    
    # Monta e envia a mensagem CONN_REQ (id_conexao ainda é 0)
    mensagem_envio = criar_cabecalho(CONN_REQ, byte_inicial, id_conexao=0) #CONN_REQ é o pedido de conexao
    meu_socket.sendto(mensagem_envio, (IP_SERVIDOR, PORTA_SERVIDOR)) #transmite mensagem via UDP para o IP e porta do servidor
    
    # Aguarda a resposta por no máximo 5 segundos
    meu_socket.settimeout(5.0)
    resposta, endereco_servidor = meu_socket.recvfrom(2048)
    
    tipo, num_msg, id_conexao, payload = ler_cabecalho(resposta)

    #se o servidor confirmar a conexao (se recebeu na mensagem o codigo 0x02 de CONN_ACK)
    if tipo == CONN_ACK:
        # Decodifica o texto do menu que o servidor mandou no payload
        menu_texto = payload.decode('utf-8', errors='ignore').rstrip('\x00') #converte os bytes em texto legivel
        print("Conexão estabelecida com sucesso!")
        return byte_inicial, id_conexao, menu_texto
        """  
        retorna o numero do byte inicial que foi gerado para informar onde a contagem comecou
        o id de conexao enviado pelo servidor
        e o texto com as musicas disponiveis
        """
    else:
        sys.exit("Erro ao tentar conectar com o servidor.")


def baixar_musica(meu_socket, id_conexao, byte_esperado, numero_musica):
    """
    Passo 2: Pede a música e fica em loop recebendo os pedaços (MUSIC_RESPONSE)
    e enviando confirmações (ACK cumulativo) até o fim (MUSIC_RESPONSE_CONCLUDED).
    """
    # Prepara o número da música como 1 byte de dados
    payload_escolha = struct.pack("B", numero_musica)
    
    # Envia o pedido MUSIC_SELECT
    pedido = criar_cabecalho(MUSIC_SELECT, byte_esperado, id_conexao, payload_escolha)
    meu_socket.sendto(pedido, (IP_SERVIDOR, PORTA_SERVIDOR))
    
    # Local na memória para ir juntando todos os pedaços do áudio
    arquivo_musica = bytearray()
    
    print(f"-> Baixando música {numero_musica}...")
    
    while True:
        resposta, _ = meu_socket.recvfrom(2048)
        tipo, num_msg, _, payload = ler_cabecalho(resposta)
        
        # Recebeu um pedaço normal da música
        if tipo == MUSIC_RESPONSE:
            # Se for o pedaço correto que estávamos esperando:
            if num_msg == byte_esperado:
                arquivo_musica.extend(payload)          # Salva os bytes na memória
                byte_esperado += len(payload)            # Avança o contador de bytes recebidos
            
            # Envia ACK dizendo qual é o PRÓXIMO byte que espera receber
            mensagem_ack = criar_cabecalho(ACK, byte_esperado, id_conexao)
            meu_socket.sendto(mensagem_ack, (IP_SERVIDOR, PORTA_SERVIDOR))
        
        # Recebeu o aviso de que a música acabou
        elif tipo == MUSIC_RESPONSE_CONCLUDED:
            # Envia o ACK final para o servidor
            mensagem_ack = criar_cabecalho(ACK, byte_esperado, id_conexao)
            meu_socket.sendto(mensagem_ack, (IP_SERVIDOR, PORTA_SERVIDOR))
            
            # Grava todos os bytes acumulados em um arquivo MP3 no computador
            nome_arquivo = f"musica_{numero_musica}.mp3"
            with open(nome_arquivo, "wb") as arquivo:
                arquivo.write(arquivo_musica)
            
            print(f"-> Download concluído! Arquivo salvo como '{nome_arquivo}'.")
            
            # Converte o novo menu recebido no payload para exibir ao usuário
            novo_menu = payload.decode('utf-8', errors='ignore').rstrip('\x00')
            return novo_menu, byte_esperado


def fechar_conexao(meu_socket, id_conexao, byte_esperado):
    """
    Passo 3: Envia a mensagem CONN_FIN informando que o cliente quer sair.
    """
    mensagem_fin = criar_cabecalho(CONN_FIN, byte_esperado, id_conexao)
    meu_socket.sendto(mensagem_fin, (IP_SERVIDOR, PORTA_SERVIDOR))
    print("-> Conexão encerrada.")

def main():
    # Cria o socket UDP
    meu_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 1. Faz o Handshake inicial
    byte_esperado, id_conexao, menu_texto = iniciar_conexao(meu_socket)
    
    # 2. Loop principal do aplicativo
    while True:
        print("\n" + menu_texto)
        opcao = input("Digite o número da música (1 a 4) ou 0 para sair: ")
        
        if not opcao.isdigit():
            print("Por favor, digite um número válido!")
            continue
            
        opcao = int(opcao)
        
        if opcao == 0:
            fechar_conexao(meu_socket, id_conexao, byte_esperado)
            break
        elif 1 <= opcao <= 4:
            menu_texto, byte_esperado = baixar_musica(meu_socket, id_conexao, byte_esperado, opcao)
        else:
            print("Opção inválida! Escolha entre 0 e 4.")

    meu_socket.close()

if __name__ == "__main__":
    main()