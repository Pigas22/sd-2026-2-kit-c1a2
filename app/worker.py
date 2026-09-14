"""
Worker: consome a fila e executa a inferencia.

O QUE JA ESTA PRONTO: o laco principal e o carregamento do modelo.
Em caso de falha a tarefa volta para a fila; apos 3 tentativas vai para a
fila de descarte (dead-letter) e o cliente passa a ver status "falhou".

Rodar:  python -m app.worker
Suba mais de um worker em terminais diferentes e veja a carga se dividir.
"""
import logging
import time

from app import fila
from app.modelo import carregar_modelo

MAX_TENTATIVAS = 3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")


def main():
    print("[worker] carregando modelo...")
    modelo = carregar_modelo()
    print("[worker] pronto. aguardando tarefas (Ctrl+C para sair)")

    while True:
        tarefa = fila.proxima_tarefa(timeout=5)
        if tarefa is None:
            continue

        tarefa_id = tarefa["id"]
        texto = tarefa["texto"]
        tamanho_entrada = len(texto.encode("utf-8"))

        print(f"[worker] processando {tarefa_id}")
        inicio = time.time()

        try:
            resultado = modelo.prever(texto)
            tempo_ms = (time.time() - inicio) * 1000

            resultado["status"] = "pronto"
            resultado["tempo_ms"] = round(tempo_ms, 2)

            # TAREFA 3: guarde o resultado para o cliente consultar depois.
            # DICA: fila.guardar_resultado(tarefa["id"], resultado)
            # raise NotImplementedError("guarde o resultado na TAREFA 3")

            fila.guardar_resultado(tarefa_id, resultado)

            logger.info(
                "tarefa_id=%s tamanho_entrada=%d "
                "tempo_resposta_ms=%.2f status=sucesso",
                tarefa_id,
                tamanho_entrada,
                tempo_ms,
            )

        except NotImplementedError:
            raise

        # ------------------------------------------------------------------
        # TAREFA 5 - retentativa e fila de descarte (dead-letter)
        # ------------------------------------------------------------------
        except Exception as erro:  # noqa: BLE001
            # TAREFA 5: retentativa + dead-letter em vez de so registrar.
            # print(f"[worker] ERRO em {tarefa['id']}: {erro}")

            tempo_ms = (time.time() - inicio) * 1000
            tarefa["tentativas"] = tarefa.get("tentativas", 0) + 1

            logger.error(
                "tarefa_id=%s tamanho_entrada=%d "
                "tempo_resposta_ms=%.2f tentativa=%d erro=%s",
                tarefa_id,
                tamanho_entrada,
                tempo_ms,
                tarefa["tentativas"],
                erro,
            )

            if tarefa["tentativas"] < MAX_TENTATIVAS:
                print(f"[worker] ERRO em {tarefa_id}: {erro} "
                      f"(tentativa {tarefa['tentativas']} de {MAX_TENTATIVAS}, "
                      f"voltando para a fila)")
                fila.reenfileirar(tarefa)
            else:
                print(f"[worker] DESCARTE de {tarefa_id} apos "
                      f"{tarefa['tentativas']} tentativas: {erro}")
                fila.descartar(tarefa, str(erro))
                fila.guardar_resultado(tarefa_id, {
                    "status": "falhou",
                    "erro": str(erro),
                    "tentativas": tarefa["tentativas"],
                })


if __name__ == "__main__":
    main()
