# arXiv
Get your daily arXiv digest

Given a list of categories to check, this program will give you a complete list with title, arxiv id, author, categories, comments and abstract. You also have the option of blacklisting certain categoies, as well as keywords in titles and abstracts for more fine grained control of your digest. Once the full list of papers satisfying all relevant criteria is presented the user may choose certain papers to download.

## Requirements

 - `python3`
 - `python-beautifulsoup4` (`pip install bs4` if you use the `python-pip` package)
 - optional: `wget` (for downloading papers)

## Setup
After specifying the settings in the settings section of `arxiv_digest.py`, give the file execution permissions with `chmod +x arxiv_digest.py` in case it doesn't already have them.

`arxiv_digest.py` listens in on a config file in `.config/arxiv.conf`. If it is not present the user will be prompted to make choices which will generate the file for subsequent use.

**E.g.**
```
[DEFAULT]

cat_whitelsit = cond-mat.mes-hall, q-bio, astro-ph

cat_blacklist = 

style = $authors-$title.pdf

colored = n
```

If `style` is not set, `%title - %authors.pdf` will be used as default.

## Example Output

```
[...]

   12 Generalized Tube Algebras, Symmetry-Resolved Partition Functions, and Twisted Boundary States (2409.02159)
      Authors: Yichul Choi, Brandon C. Rayhaun, Yunqin Zheng
      Subjects:High Energy Physics - Theory (hep-th); Strongly Correlated Electrons (cond-mat.str-el); Quantum Algebra (math.QA)
      Comments:106 pages + appendices

We introduce a class of generalized tube algebras which describe how finite, non-invertible global symmetries of bosonic 1+1d QFTs act on operators which sit at the intersection point of a collection of boundaries and interfaces. We develop a 2+1d symmetry topological field theory (SymTFT) picture of boundaries and interfaces which, among other things, allows us to deduce the representation theory of these algebras. In particular, we initiate the study of a character theory, echoing that of finite groups, and demonstrate how many representation-theoretic quantities can be expressed as partition functions of the SymTFT on various backgrounds, which in turn can be evaluated explicitly in terms of generalized half-linking numbers. We use this technology to explain how the torus and annulus partition functions of a 1+1d QFT can be refined with information about its symmetries. We are led to a vast generalization of Ishibashi states in CFT: to any multiplet of conformal boundary conditions which transform into each other under the action of a symmetry, we associate a collection of generalized Ishibashi states, in terms of which the twisted sector boundary states of the theory and all of its orbifolds can be obtained as linear combinations. We derive a generalized Verlinde formula involving the characters of the boundary tube algebra which ensures that our formulas for the twisted sector boundary states respect open-closed duality. Our approach does not rely on rationality or the existence of an extended chiral algebra; however, in the special case of a diagonal RCFT with chiral algebra $V$ and modular tensor category $\mathscr{C}$, our formalism produces explicit closed-form expressions - in terms of the $F$-symbols and $R$-matrices of $\mathscr{C}$, and the characters of $V$ - for the twisted Cardy states, and the torus and annulus partition functions decorated by Verlinde lines.

---------------------------------------------------------------------


   13 Equivariant Poincar\'e duality for cyclic groups of prime order and the Nielsen realisation problem (2409.02220)
      Authors: Kaif Hilman, Dominik Kirstein, Christian Kremer
      Subjects:Algebraic Topology (math.AT); Geometric Topology (math.GT)
      Comments:30 pages. Comments welcome!

In this companion article to [HKK24], we apply the theory of equivariant Poincaré duality developed there in the special case of cyclic groups $C_p$ of prime order to remove, in a special case, a technical condition given by Davis--Lück [DL24] in their work on the Nielsen realisation problem for aspherical manifolds. Along the way, we will also give a complete characterisation of $C_p$--Poincaré spaces as well as introduce a genuine equivariant refinement of the classical notion of virtual Poincaré duality groups which might be of independent interest.

---------------------------------------------------------------------

Which to download (e.g. 2 12 ..): 12
$HOME/Papers/arxiv-digest/Gene 100%[====================================================================================>]   1,32M  2,48MB/s    in 0,5s

```
