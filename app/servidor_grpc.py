"""
Interface gRPC do servico de inferencia.

PRE-REQUISITO: gerar os stubs antes de rodar (veja scripts/gerar_stubs).

Metodos: Prever (um texto) e PreverLote (varios textos numa chamada so).

Rodar:  python -m app.servidor_grpc
"""
from concurrent import futures
import logging
import time
import uuid

import grpc

from app.modelo import carregar_modelo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("servidor_grpc")

try:
    import inferencia_pb2
    import inferencia_pb2_grpc
except ImportError:  # pragma: no cover
    raise SystemExit(
        "Stubs nao encontrados. Rode antes:\n"
        "  python -m grpc_tools.protoc -I proto --python_out=. "
        "--grpc_python_out=. proto/inferencia.proto"
    )


class ServicoInferencia(inferencia_pb2_grpc.InferenciaServicer):

    def __init__(self):
        print("[grpc] carregando modelo...")
        self.modelo = carregar_modelo()
        print("[grpc] modelo pronto")

    def Prever(self, request, context):
        requisicao_id = str(uuid.uuid4())
        inicio = time.perf_counter()
        tamanho_entrada = len(request.texto.encode("utf-8"))

        try:
            if not request.texto.strip():
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "o texto não pode ser vazio",
                )

            r = self.modelo.prever(request.texto)
            return inferencia_pb2.RespostaPrever(
                texto=r["texto"],
                sentimento=r["sentimento"],
                confianca=r["confianca"],
            )
        finally:
            tempo_ms = (time.perf_counter() - inicio) * 1000

            logger.info(
                "requisicao_id=%s metodo=Prever tamanho_entrada=%d "
                "tempo_resposta_ms=%.2f status=%s",
                requisicao_id,
                tamanho_entrada,
                tempo_ms,
                context.code(),
            )

    # ------------------------------------------------------------------
    # TAREFA 4 - inferencia em lote
    # ------------------------------------------------------------------
    # TAREFA 4: implemente PreverLote, recebendo varios textos de uma vez.
    # def PreverLote(self, request, context):
    #     ...

    def PreverLote(self, request, context):
        requisicao_id = str(uuid.uuid4())
        inicio = time.perf_counter()
        tamanho_entrada = sum(
            len(texto.encode("utf-8")) for texto in request.textos
        )

        try:
            if not request.textos:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "o lote não pode ser vazio",
                )

            resultados = []
            for texto in request.textos:
                r = self.modelo.prever(texto)
                resultados.append(
                    inferencia_pb2.RespostaPrever(
                        texto=r["texto"],
                        sentimento=r["sentimento"],
                        confianca=r["confianca"],
                    )
                )

            return inferencia_pb2.RespostaLote(resultados=resultados)
        finally:
            tempo_ms = (time.perf_counter() - inicio) * 1000

            logger.info(
                "requisicao_id=%s metodo=PreverLote quantidade=%d "
                "tamanho_entrada=%d tempo_resposta_ms=%.2f status=%s",
                requisicao_id,
                len(request.textos),
                tamanho_entrada,
                tempo_ms,
                context.code(),
            )


def servir(porta: int = 50051):
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inferencia_pb2_grpc.add_InferenciaServicer_to_server(
        ServicoInferencia(), servidor
    )
    servidor.add_insecure_port(f"[::]:{porta}")
    servidor.start()
    print(f"[grpc] escutando na porta {porta}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    servir()
