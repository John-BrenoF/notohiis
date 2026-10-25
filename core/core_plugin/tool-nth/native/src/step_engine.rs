#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Modo {
    Continuar,
    PassoDentro,
    PassoSobre,
    PassoFora,
}

#[derive(Debug)]
pub struct MotorDePassos {
    modo: Modo,
    profundidade_inicial: usize,
}

impl MotorDePassos {
    pub fn novo() -> Self {
        MotorDePassos {
            modo: Modo::Continuar,
            profundidade_inicial: 0,
        }
    }

    pub fn definir(&mut self, modo: Modo, profundidade: usize) {
        self.modo = modo;
        self.profundidade_inicial = profundidade;
    }

    pub fn deve_parar(&self, profundidade_atual: usize) -> bool {
        match self.modo {
            Modo::Continuar => false,
            Modo::PassoDentro => true,
            Modo::PassoSobre => profundidade_atual <= self.profundidade_inicial,
            Modo::PassoFora => profundidade_atual < self.profundidade_inicial,
        }
    }
}

#[cfg(test)]
mod testes {
    use super::*;

    #[test]
    fn continuar_nunca_para_por_passo() {
        let mut motor = MotorDePassos::novo();
        motor.definir(Modo::Continuar, 3);
        assert!(!motor.deve_parar(1));
        assert!(!motor.deve_parar(3));
        assert!(!motor.deve_parar(9));
    }

    #[test]
    fn passo_dentro_para_na_proxima_linha_de_qualquer_nivel() {
        let mut motor = MotorDePassos::novo();
        motor.definir(Modo::PassoDentro, 2);
        assert!(motor.deve_parar(2));
        assert!(motor.deve_parar(3));
        assert!(motor.deve_parar(1));
    }

    #[test]
    fn passo_sobre_ignora_chamadas_mais_fundas() {
        let mut motor = MotorDePassos::novo();
        motor.definir(Modo::PassoSobre, 4);
        assert!(!motor.deve_parar(5));
        assert!(!motor.deve_parar(8));
        assert!(motor.deve_parar(4));
        assert!(motor.deve_parar(3));
    }

    #[test]
    fn passo_fora_so_para_quando_volta_para_o_chamador() {
        let mut motor = MotorDePassos::novo();
        motor.definir(Modo::PassoFora, 5);
        assert!(!motor.deve_parar(5));
        assert!(!motor.deve_parar(6));
        assert!(motor.deve_parar(4));
    }

    #[test]
    fn modo_pode_ser_redefinido_entre_passagens() {
        let mut motor = MotorDePassos::novo();
        motor.definir(Modo::PassoSobre, 2);
        assert!(!motor.deve_parar(3));
        assert!(motor.deve_parar(2));
        motor.definir(Modo::PassoFora, 7);
        assert!(!motor.deve_parar(7));
        assert!(motor.deve_parar(6));
    }
}
