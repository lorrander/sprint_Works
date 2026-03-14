CREATE TABLE produtos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100),
    preco DECIMAL,
    custo DECIMAL,
    estoque INT
);

CREATE TABLE vendas (
    id SERIAL PRIMARY KEY,
    produto_id INT,
    quantidade INT,
    valor_total DECIMAL,
    vendedor VARCHAR(100),
    data TIMESTAMP
);
