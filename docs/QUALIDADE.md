# Qualidade E CI/CD

## Comandos Locais

Comando único:

```powershell
npm run check
```

Frontend:

```powershell
npm run check:frontend
```

Backend:

```powershell
npm run check:backend
```

Formatação:

```powershell
npm run format
npm run format:check
```

## Pipeline GitHub Actions

Workflow: `.github/workflows/ci.yml`.

Jobs:

- Prettier: `npm run format:check`.
- Frontend: `npm run lint`, `npx tsc --noEmit`, `npm run build`.
- Backend: `python -m pytest tests/ -q`.
- Quality gate: só passa se todos os jobs anteriores passarem.

## Bloqueio De Merge

Para bloquear merge no GitHub:

1. Abra Settings -> Branches.
2. Crie ou edite a regra da branch `main`/`master`.
3. Ative "Require status checks to pass before merging".
4. Marque o status **Quality gate** como obrigatório.
5. Ative "Require branches to be up to date before merging", se o fluxo exigir.

Com isso, PR com lint, TypeScript, build, Prettier ou pytest falhando não entra.

## Pre-Commit

Ative uma vez por clone:

```powershell
.\scripts\install-git-hooks.ps1
```

O hook `.githooks/pre-commit` executa:

1. `npm run format`
2. `npm run lint`

Se o Prettier alterar arquivos, o commit é bloqueado para você revisar e adicionar as mudanças formatadas.

## Ordem Recomendada De Qualidade

1. Corrigir testes Python.
2. Corrigir TypeScript.
3. Corrigir lint.
4. Rodar Prettier.
5. Rodar build.
6. Rodar suíte completa.
7. Abrir PR.

## Critério De Pronto

Uma alteração só está pronta quando:

- `npm run check` passa.
- O CI passa.
- A documentação foi atualizada se fluxo, API, risco ou operação mudaram.
- Não há segredo novo versionado.
- `config/live.yaml` não foi alterado automaticamente por defaults de teste.
