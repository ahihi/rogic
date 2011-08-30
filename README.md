# rogic

A recursive-descent parser and evaluator for propositional logic expressions, because I was bored.

## Example session

    $ python rogic.py 
    Define atoms by entering lines of the form:
        atomname = value
    where value is 1 or 0. Enter a blank line when done.
    def> a = 1
    def> b = 0
    def> c = 1
    def> 
    Now enter expressions such as:
        ¬a ∧ (b ∨ c)
    to evaluate their truth values.
    eval> ¬a ∧ (b ∨ c)
    0
    eval> _

## License

Public domain!