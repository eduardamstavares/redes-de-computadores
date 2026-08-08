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

# Configuracoes do Servidor

IP_SERVIDOR = "52.67.245.39"
PORTA_SERVIDOR = 50000

# Codigos das mensagens do protocolo

CONN_REQ = 0x01
CONN_ACK = 0x02
MUSIC_SELECT = 0x03
MUSIC_RESPONSE = 0x04
MUSIC_RESPONSE_CONCLUDED = 0x05
ACK = 0x06
CONN_FIN = 0x07

# Erros que o servidor pode mandar

TOO_SHORT_ERR = 0x08
TOO_LONG_ERR = 0x09
INVALID_CONN = 0x0A
INVALID_MUSIC = 0x0B
INVALID_MSG = 0x0C

#funções

def criar_cabecalho(tipo: int, num_msg: int, num_conexao: int, payload: bytes = b"") -> bytes:

    # Junta o cabeçalho de 7 bytes (little-endian) com os dados (payload)

    cabecalho = struct.pack("<BIH", tipo, num_msg, num_conexao)
    return cabecalho + payload


def ler_cabecalho(mensagem: bytes):

    if len(mensagem) < 7:
        raise ValueError("Mensagem muito curta, menor que 7 bytes.")
    
    tipo, num_msg, num_conexao = struct.unpack("<BIH", mensagem[:7])
    payload = mensagem[7:]
    return tipo, num_msg, num_conexao, payload


def iniciar_conexao(meu_socket):

    # Gera o numero inicial e envia a requisicao de conexao

    byte_inicial = random.randint(1, 0x00FFFFFF)
    mensagem_envio = criar_cabecalho(CONN_REQ, byte_inicial, 0)
    meu_socket.sendto(mensagem_envio, (IP_SERVIDOR, PORTA_SERVIDOR))
    meu_socket.settimeout(3.0)
    
    while True:
        try:

            resposta, _ = meu_socket.recvfrom(2048)
            tipo, num_msg_servidor, id_conexao, payload = ler_cabecalho(resposta)

            if tipo == CONN_ACK:

                menu_texto = payload.decode('utf-8', errors='ignore').rstrip('\x00')
                print("Conexão estabelecida com sucesso!")
                return byte_inicial, num_msg_servidor, id_conexao, menu_texto
            
            else:

                print(f"Resposta inesperada do servidor: {tipo}")

        except socket.timeout:

            print("Timeout aguardando conexao... Retransmitindo pedido.")
            meu_socket.sendto(mensagem_envio, (IP_SERVIDOR, PORTA_SERVIDOR))


def baixar_musica(meu_socket, id_conexao, byte_cliente, byte_inicial_servidor, numero_musica):

    # Envia qual musica queremos baixar

    payload_escolha = struct.pack("B", numero_musica)
    pedido = criar_cabecalho(MUSIC_SELECT, byte_cliente, id_conexao, payload_escolha)
    meu_socket.sendto(pedido, (IP_SERVIDOR, PORTA_SERVIDOR))
    
    buffer_pacotes = {}
    byte_esperado = byte_inicial_servidor
    novo_menu = ""
    
    print(f"-> Baixando música {numero_musica}...")
    
    while True:
        try:
            resposta, _ = meu_socket.recvfrom(2048)
            tipo, num_msg, _, payload = ler_cabecalho(resposta)
            
            # Trata se o servidor mandar algum aviso de erro

            if TOO_SHORT_ERR <= tipo <= INVALID_MSG:

                print(f"Servidor retornou erro codigo: {tipo}")
                break

            if tipo in (MUSIC_RESPONSE, MUSIC_RESPONSE_CONCLUDED):
                
                if tipo == MUSIC_RESPONSE_CONCLUDED:

                    # Separa o trecho final do audio do texto do menu

                    partes = payload.split(b'\x00', 1)
                    dados_audio = partes[0]
                    if len(partes) > 1:
                        novo_menu = partes[1].decode('utf-8', errors='ignore')
                    if dados_audio:
                        buffer_pacotes[num_msg] = dados_audio
                else:
                    if num_msg >= byte_esperado:
                        buffer_pacotes[num_msg] = payload
                
                # Anda com o contador do ACK ate o ponto onde temos dados continuos

                while byte_esperado in buffer_pacotes:
                    byte_esperado += len(buffer_pacotes[byte_esperado])
                
                # Manda o ACK cumulativo informando o proximo byte que aguardamos

                mensagem_ack = criar_cabecalho(ACK, byte_esperado, id_conexao)
                meu_socket.sendto(mensagem_ack, (IP_SERVIDOR, PORTA_SERVIDOR))
                
                if tipo == MUSIC_RESPONSE_CONCLUDED:
                    print("-> Download concluído!")
                    break

        except socket.timeout:

            # Se perder pacote ou o servidor demorar, reenvia o ACK do ultimo ponto que é conhecido

            mensagem_ack = criar_cabecalho(ACK, byte_esperado, id_conexao)
            meu_socket.sendto(mensagem_ack, (IP_SERVIDOR, PORTA_SERVIDOR))

    # Reagrupa os pedacos de audio em ordem

    arquivo_musica = bytearray()
    for pos in sorted(buffer_pacotes.keys()):
        arquivo_musica.extend(buffer_pacotes[pos])

    # Salva o arquivo no computador
    nome_arquivo = f"musica_{numero_musica}.mp3"
    with open(nome_arquivo, "wb") as arquivo:
        arquivo.write(arquivo_musica)
    print(f"-> Arquivo salvo como '{nome_arquivo}'.")

    return novo_menu, byte_esperado


def fechar_conexao(meu_socket, id_conexao, byte_esperado):

    mensagem_fin = criar_cabecalho(CONN_FIN, byte_esperado, id_conexao)
    meu_socket.sendto(mensagem_fin, (IP_SERVIDOR, PORTA_SERVIDOR))
    print("-> Conexão encerrada.")


def main():
    meu_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # 1. Faz o Handshake inicial

        byte_cliente, byte_esperado, id_conexao, menu_texto = iniciar_conexao(meu_socket)
        
        # 2. Loop principal

        while True:
            print("\n" + menu_texto)
            opcao = input("Digite o número da música (1 a 4) ou 0 para sair: ")
            
            if not opcao.isdigit():
                print("Por favor, digite um número válido!")
                continue
                
            opcao = int(opcao)
            
            if opcao == 0:
                fechar_conexao(meu_socket, id_conexao, byte_cliente)
                break
            elif 1 <= opcao <= 4:
                menu_texto, byte_esperado = baixar_musica(
                    meu_socket, id_conexao, byte_cliente, byte_esperado, opcao
                )
                byte_cliente += 1
            else:
                print("Opção inválida! Escolha entre 0 e 4.")

    except Exception as e:
        print(f"Ocorreu um erro no programa: {e}")
    finally:
        meu_socket.close()

if __name__ == "__main__":
    main()
