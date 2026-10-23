# Engenharia reversa — app CAERN

Alvo: `br.com.caern.mobile.caernmobile` v1.9.7-90, APK da APKPure, analisado
estaticamente com `jadx` (nunca executado). App Android nativo Java/Kotlin, com
o pacote `br.com.caern.mobile.caernmobile.network` **não ofuscado** (Retrofit).

## Backend e autenticação

- Base REST: `https://servermobile.caern.com.br/rest/` (string
  `base_url_producao`). Cliente OkHttp padrão, timeout 90s, sem pinning real.
- **Autenticação = Firebase Auth.** O app loga por e-mail/senha, Google ou
  Facebook (`LoginController`, `ActivityLogin`) e usa o **ID token do Firebase**
  (`currentUser.getIdToken(true)`) como header **`Authorization`** — valor **cru**
  (sem prefixo `Bearer`), passado em cada método via `@Header("Authorization")`.
- Projeto Firebase `caernmobile`, chave `google_api_key` =
  `AIzaSyCeahuUfDsqsCcaiPTv4Gf0WTEuJjg0cgo`.
- Esta integração replica o login **e-mail/senha** via Firebase REST:
  `identitytoolkit …accounts:signInWithPassword?key=` para obter `idToken` +
  `refreshToken`, e `securetoken …/token` para renovar (token expira em ~1h).
  Contas sociais (Google/Facebook) não têm senha e não funcionam headless.
- Envelope de resposta: `Response<T> = { status, message, type, content }` — o
  dado real está em `content`.

## Endpoints usados (interfaces em `network/interfaces/*`)

| Endpoint | Retorno | Uso |
|---|---|---|
| `GET imovel` | `List<Imovel>` | imóveis (matrículas) do usuário — âncora |
| `GET imovel/{matricula}` | `Imovel` | detalhe do imóvel |
| `GET conta?matricula=&incluir_pagas_30_dias=` | `List<Conta>` | contas (abertas + pagas recentes) |
| `GET conta/{idConta}` | `Conta` | detalhe (código de barras, PIX copia-e-cola) |
| `GET contas_pagas?matricula=&ano=` | `List<Conta>` | contas pagas do ano |
| `GET historicoconsumo/{matricula}` | `List<HistoricoConsumo>` | consumo mensal (m³) |
| `GET quantidades` | `Quantidades` | resumo: contas abertas, imóveis, registros |
| `GET ocorrencia_operacional_por_imovel/todos` | `List<OcorrenciaOperacional>` | faltas d'água/obras |
| `GET segundavia/{idConta}` | `String` | 2ª via |
| `GET v2/listar_debitos` | — | débitos |

Ações: `PUT imovel/{matricula}?cpfCnpj=` (vincular), `DELETE imovel/{matricula}`
(desvincular), `POST autoleitura/envio` (autoleitura).

## Modelos principais

- **Conta**: `valor`, `valorAgua`, `valorEsgoto`, `dataVencimento`,
  `dataPagamento`, `paga`, `situacao`, `anoMes`, `consumoMedido`,
  `consumoFaturado`, `mediaMes`, `leituraAtual`, `leituraAnterior`,
  `codigoBarras`, `qrCodePix`, `nomeCliente`, `itens[]`.
- **Imovel**: `matricula`, `endereco`, `inscricao`, `situacaoAgua`,
  `situacaoEsgoto`, `autoLeitura`, `historicoConsumo[]`,
  `ocorrenciaOperacionalAtiva`.
- **HistoricoConsumo**: `anoMes`, `consumo`, `consumoMedio`.
- **Quantidades**: `contas`, `imoveis`, `registrosAbertos`.
- **OcorrenciaOperacional**: `motivo`, `descricao`, `areasAfetadas`,
  `dataAbertura`, `dataPrevisaoNormalizacao`.

## Outros endpoints mapeados (referência, não expostos)

`agendamento*` (agendamentos de atendimento), `religacao`, `parcelamento*`
(negociação de dívida), `linkpagamento`/`PagamentoCartao`, `tarifas`,
`tarifaSocial`, `mensagem`, `registroatendimento`, `novaLigacao*`,
`municipio`/`bairro`/`logradouro`, `aceite_termo_uso`, `chat`, `status_email`.
Total: 62 endpoints em `network/interfaces/*`.
