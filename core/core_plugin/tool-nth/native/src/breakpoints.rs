use std::collections::{BTreeSet, HashMap};

use pyo3::prelude::*;

#[derive(Default)]
struct EstadoLeitura {
    dentro_tripla: Option<char>,
    profundidade: i32,
}

fn varrer_linha(linha: &str, estado: &mut EstadoLeitura) -> (bool, bool) {
    let caracteres: Vec<char> = linha.chars().collect();
    let mut tem_codigo = false;
    let mut continuacao = false;
    let mut posicao = 0usize;
    while posicao < caracteres.len() {
        let atual = caracteres[posicao];
        if let Some(aspa) = estado.dentro_tripla {
            if atual == '\\' {
                posicao += 2;
                continue;
            }
            if atual == aspa
                && posicao + 2 < caracteres.len()
                && caracteres[posicao + 1] == aspa
                && caracteres[posicao + 2] == aspa
            {
                estado.dentro_tripla = None;
                posicao += 3;
                continue;
            }
            posicao += 1;
            continue;
        }
        match atual {
            '#' => break,
            '\\' => {
                continuacao = true;
                posicao += 1;
            }
            '\'' | '"' => {
                if posicao + 2 < caracteres.len()
                    && caracteres[posicao + 1] == atual
                    && caracteres[posicao + 2] == atual
                {
                    estado.dentro_tripla = Some(atual);
                    posicao += 3;
                    tem_codigo = true;
                    continue;
                }
                posicao += 1;
                while posicao < caracteres.len() {
                    if caracteres[posicao] == '\\' {
                        posicao += 2;
                        continue;
                    }
                    if caracteres[posicao] == atual {
                        posicao += 1;
                        break;
                    }
                    posicao += 1;
                }
                tem_codigo = true;
            }
            '(' | '[' | '{' => {
                estado.profundidade += 1;
                tem_codigo = true;
                posicao += 1;
            }
            ')' | ']' | '}' => {
                estado.profundidade -= 1;
                if estado.profundidade < 0 {
                    estado.profundidade = 0;
                }
                tem_codigo = true;
                posicao += 1;
            }
            outro => {
                if !outro.is_whitespace() {
                    tem_codigo = true;
                }
                posicao += 1;
            }
        }
    }
    (tem_codigo, continuacao && estado.dentro_tripla.is_none())
}

#[pyfunction]
pub fn linhas_executaveis(conteudo: &str) -> Vec<usize> {
    let mut resultado = Vec::new();
    let mut estado = EstadoLeitura::default();
    let mut anterior_continuada = false;
    for (indice, bruta) in conteudo.lines().enumerate() {
        let comecou_dentro_de_texto = estado.dentro_tripla.is_some();
        let comecou_em_nivel = estado.profundidade;
        let (tem_codigo, continuacao) = varrer_linha(bruta, &mut estado);
        let executavel = !comecou_dentro_de_texto
            && !anterior_continuada
            && comecou_em_nivel == 0
            && tem_codigo;
        if executavel {
            resultado.push(indice + 1);
        }
        anterior_continuada = continuacao;
    }
    resultado
}

#[derive(Default)]
pub struct PontosDeParada {
    arquivos: HashMap<String, BTreeSet<usize>>,
}

impl PontosDeParada {
    pub fn novo() -> Self {
        Self::default()
    }

    pub fn alternar(&mut self, arquivo: &str, linha: usize) -> bool {
        let conjunto = self.arquivos.entry(arquivo.to_string()).or_default();
        if conjunto.contains(&linha) {
            conjunto.remove(&linha);
            false
        } else {
            conjunto.insert(linha);
            true
        }
    }

    pub fn definir(&mut self, arquivo: &str, linhas: &[usize]) {
        let conjunto = self.arquivos.entry(arquivo.to_string()).or_default();
        conjunto.clear();
        for linha in linhas {
            conjunto.insert(*linha);
        }
    }

    pub fn limpar(&mut self) {
        self.arquivos.clear();
    }

    pub fn linhas(&self, arquivo: &str) -> Vec<usize> {
        self.arquivos
            .get(arquivo)
            .map(|conjunto| conjunto.iter().copied().collect())
            .unwrap_or_default()
    }

    pub fn todos(&self) -> Vec<(String, Vec<usize>)> {
        let mut lista: Vec<(String, Vec<usize>)> = self
            .arquivos
            .iter()
            .map(|(arquivo, conjunto)| {
                (arquivo.clone(), conjunto.iter().copied().collect())
            })
            .collect();
        lista.sort_by(|a, b| a.0.cmp(&b.0));
        lista
    }

    pub fn contem(&self, arquivo: &str, linha: usize) -> bool {
        self.arquivos
            .get(arquivo)
            .map(|conjunto| conjunto.contains(&linha))
            .unwrap_or(false)
    }
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn linhas_em_branco_e_comentario_nao_contam() {
        let fonte = "\n# comentário\n\n    \n\nx = 1\n";
        assert_eq!(linhas_executaveis(fonte), vec![6]);
    }

    #[test]
    fn comentario_apos_codigo_continua_sendo_executavel() {
        let fonte = "x = 1  # ok\n# y = 2\n";
        assert_eq!(linhas_executaveis(fonte), vec![1]);
    }

    #[test]
    fn texto_triplo_nao_vira_linha_executavel() {
        let fonte = "doc = \"\"\"\nlinha dentro\ncolorir = 1\n\"\"\"\nfim = 2\n";
        assert_eq!(linhas_executaveis(fonte), vec![1, 5]);
    }

    #[test]
    fn hash_dentro_de_string_nao_fecha_a_linha() {
        let fonte = "url = \"http://a#b\" + \"#c\"\n";
        assert_eq!(linhas_executaveis(fonte), vec![1]);
    }

    #[test]
    fn continuacao_de_colchete_nao_conta() {
        let fonte = "chamar(\n    1,\n    2,\n)\npronto = True\n";
        assert_eq!(linhas_executaveis(fonte), vec![1, 5]);
    }

    #[test]
    fn continuacao_de_barra_escondida_seguinte() {
        let fonte = "total = 1 + \\\n    2\noutro = 3\n";
        assert_eq!(linhas_executaveis(fonte), vec![1, 3]);
    }

    #[test]
    fn decorador_e_else_contam() {
        let fonte = "@decorar\ndef f():\n    pass\nelse_ = 0\n";
        assert_eq!(linhas_executaveis(fonte), vec![1, 2, 3, 4]);
    }

    #[test]
    fn string_que_abre_e_fecha_na_mesma_linha() {
        let fonte = "a = \"\"\"x\"\"\"\nb = 'y'\nc = f\"{a} z\"\n";
        assert_eq!(linhas_executaveis(fonte), vec![1, 2, 3]);
    }

    #[test]
    fn pontos_de_parada_alternam_ordenados_e_sem_duplicata() {
        let mut pontos = PontosDeParada::novo();
        assert!(pontos.alternar("/a.py", 5));
        assert!(pontos.alternar("/a.py", 2));
        assert!(!pontos.alternar("/a.py", 5));
        assert!(pontos.alternar("/a.py", 5));
        pontos.definir("/b.py", &[9, 3, 3]);
        assert_eq!(pontos.linhas("/a.py"), vec![2, 5]);
        assert_eq!(pontos.linhas("/b.py"), vec![3, 9]);
        assert!(pontos.contem("/a.py", 5));
        assert!(!pontos.contem("/a.py", 7));
        let todos = pontos.todos();
        assert_eq!(todos.len(), 2);
        assert_eq!(todos[0].0, "/a.py");
        assert_eq!(todos[1].0, "/b.py");
    }

    #[test]
    fn limpar_zera_os_arquivos() {
        let mut pontos = PontosDeParada::novo();
        pontos.alternar("/a.py", 1);
        pontos.limpar();
        assert!(pontos.todos().is_empty());
        assert!(!pontos.contem("/a.py", 1));
    }
}
