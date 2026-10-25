use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Quadro {
    pub nome: String,
    pub arquivo: String,
    pub linha: usize,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Variavel {
    pub nome: String,
    pub valor: String,
    pub tipo: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Evento {
    Conectado,
    Parado {
        motivo: String,
        arquivo: String,
        linha: usize,
        quadros: Vec<Quadro>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        detalhe: Option<String>,
    },
    Continuado,
    Variaveis {
        id: u64,
        locais: Vec<Variavel>,
        globais: Vec<Variavel>,
    },
    Avaliado {
        id: u64,
        resultado: String,
        erro: Option<String>,
    },
    Saida {
        fluxo: String,
        texto: String,
    },
    Saiu {
        codigo: i32,
    },
    Erro {
        mensagem: String,
    },
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "cmd", rename_all = "snake_case")]
pub enum Comando {
    DefinirPontos {
        arquivo: String,
        linhas: Vec<usize>,
    },
    Continuar,
    PassoSobre,
    PassoDentro,
    PassoFora,
    Pausar,
    Pronto,
    Encerrar,
    Variaveis {
        id: u64,
        quadro: usize,
    },
    Avaliar {
        id: u64,
        quadro: usize,
        expressao: String,
    },
}

pub fn serializar<T: Serialize>(valor: &T) -> Option<String> {
    serde_json::to_string(valor).ok()
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn parado_omite_detalhe_quando_vazio() {
        let evento = Evento::Parado {
            motivo: "breakpoint".to_string(),
            arquivo: "/a/b.py".to_string(),
            linha: 3,
            quadros: Vec::new(),
            detalhe: None,
        };
        let texto = serializar(&evento).unwrap();
        assert!(texto.contains("\"type\":\"parado\""));
        assert!(!texto.contains("detalhe"));
    }

    #[test]
    fn parado_com_detalhe_sobrevive_a_ida_e_volta() {
        let original = Evento::Parado {
            motivo: "excecao".to_string(),
            arquivo: "/a/b.py".to_string(),
            linha: 9,
            quadros: vec![Quadro {
                nome: "principal".to_string(),
                arquivo: "/a/b.py".to_string(),
                linha: 9,
            }],
            detalhe: Some("ValueError: errou".to_string()),
        };
        let texto = serializar(&original).unwrap();
        let volta: Evento = serde_json::from_str(&texto).unwrap();
        assert_eq!(volta, original);
    }

    #[test]
    fn comandos_unitarios_tem_o_campo_de_comando() {
        let texto = serializar(&Comando::Continuar).unwrap();
        assert_eq!(texto, "{\"cmd\":\"continuar\"}");
        let pronto = serializar(&Comando::Pronto).unwrap();
        assert_eq!(pronto, "{\"cmd\":\"pronto\"}");
    }

    #[test]
    fn variaveis_e_avaliacao_carregam_o_identificador() {
        let variaveis = Comando::Variaveis { id: 7, quadro: 1 };
        let texto = serializar(&variaveis).unwrap();
        let volta: Comando = serde_json::from_str(&texto).unwrap();
        assert_eq!(volta, variaveis);

        let avaliar = Comando::Avaliar {
            id: 8,
            quadro: 0,
            expressao: "x + 1".to_string(),
        };
        let texto = serializar(&avaliar).unwrap();
        let volta: Comando = serde_json::from_str(&texto).unwrap();
        assert_eq!(volta, avaliar);
    }

    #[test]
    fn resposta_de_variaveis_e_reconhecida_pelo_tipo() {
        let texto = "{\"type\":\"variaveis\",\"id\":2,\"locais\":[{\"nome\":\"x\",\"valor\":\"1\",\"tipo\":\"int\"}],\"globais\":[]}";
        let evento: Evento = serde_json::from_str(texto).unwrap();
        match evento {
            Evento::Variaveis { id, locais, .. } => {
                assert_eq!(id, 2);
                assert_eq!(locais.len(), 1);
                assert_eq!(locais[0].nome, "x");
                assert_eq!(locais[0].valor, "1");
                assert_eq!(locais[0].tipo, "int");
            }
            outro => panic!("esperava variaveis, veio {:?}", outro),
        }
    }

    #[test]
    fn saida_e_saida_com_codigo_carregam_os_campos() {
        let texto = "{\"type\":\"saida\",\"fluxo\":\"stdout\",\"texto\":\"oi\\n\"}";
        let evento: Evento = serde_json::from_str(texto).unwrap();
        assert_eq!(
            evento,
            Evento::Saida {
                fluxo: "stdout".to_string(),
                texto: "oi\n".to_string()
            }
        );

        let texto = "{\"type\":\"saiu\",\"codigo\":0}";
        let evento: Evento = serde_json::from_str(texto).unwrap();
        assert_eq!(
            evento,
            Evento::Saiu {
                codigo: 0
            }
        );
    }
}
