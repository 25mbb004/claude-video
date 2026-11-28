"""Build De_Novo_Protein_Design_Presentation.pptx (python-pptx).

Every persistent object (the "cast") is re-created on every slide with the same `!!Name`,
changing only position / size / rotation / fill / text, so PowerPoint's Morph transition
can pair them across slides. Non-persistent objects get ordinary unique names and just fade.
"""
import os
from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
OUT = os.path.join(HERE, "..", "De_Novo_Protein_Design_Presentation.pptx")

# ---------- palette & type ----------
BG, WHITE, MINT, GREEN = "F4FAF5", "FFFFFF", "DDF1E3", "2F8F5B"
FOREST, EMER, LIME, AMBER, AMBER_PALE = "14301F", "10B981", "B5E36B", "D97706", "FDF0DC"
BG_WARM = "FBF4E6"
HEAD, BODY = "Segoe UI Semibold", "Segoe UI"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def rgb(h):
    return RGBColor.from_string(h)


# ---------- low-level helpers ----------
def place(shape, cx, cy, w, h, rot=0):
    shape.left, shape.top = Inches(cx - w / 2), Inches(cy - h / 2)
    shape.width, shape.height = Inches(w), Inches(h)
    shape.rotation = rot


def shadow(shape, on=True):
    spPr = shape._element.spPr
    for old in spPr.findall(qn("a:effectLst")):
        spPr.remove(old)
    eff = etree.SubElement(spPr, qn("a:effectLst"))
    if on:
        sh = etree.SubElement(eff, qn("a:outerShdw"), blurRad="228600", dist="50800", dir="5400000", algn="t", rotWithShape="0")
        c = etree.SubElement(sh, qn("a:srgbClr"), val=GREEN)
        etree.SubElement(c, qn("a:alpha"), val="15000")


def fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(color)
    shape.line.fill.background()


def R(text, size=20, color=FOREST, font=BODY, italic=False, bold=False, sup=False):
    return dict(text=text, size=size, color=color, font=font, italic=italic, bold=bold, sup=sup)


def write(tf, paras, anchor=MSO_ANCHOR.MIDDLE, margins=(0.2, 0.1, 0.2, 0.1), align=PP_ALIGN.LEFT):
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = (Inches(m) for m in margins)
    tf.vertical_anchor = anchor
    first = True
    for p in paras:
        runs, after = (p["runs"], p.get("after", 0)) if isinstance(p, dict) else (p, 0)
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        para.alignment = (p.get("align") if isinstance(p, dict) and p.get("align") is not None else align)
        para.space_after = Pt(after)
        for r in runs:
            run = para.add_run()
            run.text = r["text"]
            f = run.font
            f.size, f.name, f.bold, f.italic = Pt(r["size"]), r["font"], r["bold"], r["italic"]
            f.color.rgb = rgb(r["color"])
            if r["sup"]:
                run._r.get_or_add_rPr().set("baseline", "30000")


def rounded(slide, name, cx, cy, w, h, color, shadow_on=True, radius=0.17):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, 0, 0, 1, 1)
    s.name = name
    place(s, cx, cy, w, h)
    s.adjustments[0] = min(0.5, radius / min(w, h))
    fill(s, color)
    shadow(s, shadow_on)
    return s


def picture(slide, name, file, cx, cy, w, h=None, rot=0, alpha=None, alt=""):
    path = os.path.join(ASSETS, file)
    iw, ih = Image.open(path).size
    h = h if h is not None else w * ih / iw
    p = slide.shapes.add_picture(path, 0, 0, Inches(w), Inches(h))
    p.name = name
    place(p, cx, cy, w, h, rot)
    p._element.nvPicPr.cNvPr.set("descr", alt)
    if alpha is not None:
        blip = p._element.blipFill.find(qn("a:blip"))
        etree.SubElement(blip, qn("a:alphaModFix"), amt=str(int(alpha * 1000)))
    return p


def textbox(slide, name, cx, cy, w, h, paras, anchor=MSO_ANCHOR.TOP, margins=(0, 0, 0, 0), align=PP_ALIGN.LEFT):
    t = slide.shapes.add_textbox(0, 0, 1, 1)
    t.name = name
    place(t, cx, cy, w, h)
    write(t.text_frame, paras, anchor, margins, align)
    return t


def line(slide, name, x1, y1, x2, y2, color, width=2.5, arrow=False, curved=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.CURVE if curved else MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.name = name
    if curved:
        c._element.spPr.find(qn("a:prstGeom")).set("prst", "curvedConnector2")
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    if arrow:
        ln = c.line._get_or_add_ln()
        etree.SubElement(ln, qn("a:tailEnd"), type="triangle", w="med", len="med")
    return c


def glyph(slide, name, kind, cx, cy, d, circle_fill, glyph_fill, bang=False):
    c = slide.shapes.add_shape(MSO_SHAPE.OVAL, 0, 0, 1, 1)
    c.name = name + "_bg"
    place(c, cx, cy, d, d)
    fill(c, circle_fill)
    shadow(c, False)
    g = slide.shapes.add_shape(kind, 0, 0, 1, 1)
    g.name = name
    place(g, cx, cy + (0.02 if bang else 0), d * 0.52, d * 0.52)
    fill(g, glyph_fill)
    shadow(g, False)
    if bang:
        write(g.text_frame, [[R("!", 14, WHITE, HEAD)]], MSO_ANCHOR.MIDDLE, (0, 0, 0, 0), PP_ALIGN.CENTER)


# ---------- cast state tables (cx, cy, w, h, rot) ----------
# Persistent pictures. h is derived from the PNG aspect unless given.
BLOB_A = {1: (1.0, 7.0, 9.0, 0), 2: (0.6, 6.3, 8.4, -6), 3: (7.6, 6.9, 8.0, 8), 4: (0.2, 7.4, 3.6, 0),
          5: (2.0, 7.9, 5.4, 10), 6: (0.4, 7.6, 4.6, -4), 7: (1.5, 7.0, 8.6, 0), 8: (0.3, 7.6, 4.5, 0)}
BLOB_B = {1: (12.2, 0.9, 3.0, 0), 2: (12.7, 2.9, 2.6, 25), 3: (0.4, 1.6, 3.4, -15), 4: (13.1, 0.2, 1.7, 0),
          5: (12.9, 7.2, 3.0, 20), 6: (13.0, 7.0, 2.6, -20), 7: (12.3, 0.9, 3.0, 0), 8: (13.0, 0.3, 1.8, 0)}
HELIX = {1: (10.0, 3.9, 6.6, 15), 2: (11.7, 1.5, 2.6, 30), 3: (6.67, 3.95, 3.8, -20), 4: (12.0, 6.62, 0.95, 10),
         5: (11.0, 4.0, 5.0, -10), 6: (12.4, 1.1, 1.6, -25), 7: (10.8, 3.9, 6.2, 12), 8: (11.8, 6.1, 1.7, 0)}
STRAND = {1: (6.67, 7.0, 12.5, 1.5, 0), 2: (2.6, 6.95, 4.8, 0.8, -2), 3: (9.5, 1.3, 6.5, 0.9, 0),
          4: (5.6, 4.22, 10.0, 0.55, 0), 5: (2.4, 7.05, 5.0, 0.65, 0), 6: (2.4, 7.0, 5.0, 0.7, 0),
          7: (2.4, 6.95, 5.0, 0.8, 0), 8: (2.4, 7.0, 5.0, 0.7, 0)}
ALPHA = {6: 45, 8: 45}  # blobs fade on slides 6 and 8

# Grid used for the cards on slide 3
CW, CH, X0, X1, Y0, Y1 = 5.9, 2.0, 0.6, 6.83, 1.85, 4.13
S3_POS = [(X0 + CW / 2, Y0 + CH / 2), (X1 + CW / 2, Y0 + CH / 2), (X0 + CW / 2, Y1 + CH / 2), (X1 + CW / 2, Y1 + CH / 2)]
# Slide 4 flowchart geometry
NW, NH, NSTEP = 2.7, 1.55, 3.14
R1Y, R2Y = 2.3 + NH / 2, 4.6 + NH / 2
NODE_POS = [(0.6 + NW / 2 + i * NSTEP, R1Y) for i in range(4)]
N5 = (0.6 + NW / 2 + 3 * NSTEP, R2Y)
N6 = (0.6 + NW / 2 + 2 * NSTEP, R2Y)
ARROWS = [  # cx, cy, rot
    (NODE_POS[0][0] + NW / 2 + 0.22, R1Y, 0), (NODE_POS[1][0] + NW / 2 + 0.22, R1Y, 0), (NODE_POS[2][0] + NW / 2 + 0.22, R1Y, 0),
    (NODE_POS[3][0], R1Y + NH / 2 + 0.38, 90), (N6[0] + NW / 2 + 0.22, R2Y, 180)]
# Slide 5 grid (2x2)
S5W, S5H = 4.1, 2.2
S5_POS = [(0.6 + S5W / 2, 1.8 + S5H / 2), (5.0 + S5W / 2, 1.8 + S5H / 2), (0.6 + S5W / 2, 4.2 + S5H / 2), (5.0 + S5W / 2, 4.2 + S5H / 2)]
# Slide 6 row
S6W, S6H, S6Y = 2.85, 3.0, 2.2
S6_POS = [(0.6 + S6W / 2 + i * 3.09, S6Y + S6H / 2) for i in range(4)]
# Slide 7 pills
S7W, S7H = 8.3, 1.25
S7_POS = [(0.6 + S7W / 2, 1.9 + S7H / 2 + i * 1.5) for i in range(3)]

NOT_YET = 6.0  # cards wait this far below their slide-3 spot (they fly up)
GONE_Y = 8.7


def card_state(n, i):
    """Return dict for Card{i+1} on slide n (i = 0..3)."""
    s3 = dict(pos=S3_POS[i], size=(CW, CH), fill=WHITE, shadow=True)
    if n in (1, 2):
        return dict(s3, pos=(S3_POS[i][0], S3_POS[i][1] + NOT_YET), kind="s3")
    if n == 3:
        return dict(s3, kind="s3")
    if n == 4:
        return dict(pos=NODE_POS[i], size=(NW, NH), fill=[ "D9F0E1", "C8EAD5", "B7E4C8", GREEN][i], shadow=True, kind="node")
    if n == 5:
        return dict(pos=S5_POS[i], size=(S5W, S5H), fill=WHITE, shadow=True, kind="s5")
    if n == 6:
        return dict(pos=S6_POS[i], size=(S6W, S6H), fill=WHITE, shadow=True, kind="s6")
    if n == 7:
        if i < 3:
            return dict(pos=S7_POS[i], size=(S7W, S7H), fill=MINT, shadow=True, kind="s7", radius=0.45)
        return dict(pos=(6.67, GONE_Y), size=(2.0, 1.0), fill=MINT, shadow=False, kind="gone")
    return dict(pos=(S7_POS[min(i, 2)][0], GONE_Y), size=(S7W, S7H), fill=MINT, shadow=False, kind="gone")


S3_TEXT = [("De novo", "“From new”: not derived from any existing protein"),
           ("Backbone", "Structural skeleton, without side chains"),
           ("Generative model", "AI that creates new examples, not just classifies"),
           ("Binder", "Protein designed to stick tightly to one target")]
NODE_TEXT = [("1", "Specify the goal", "e.g. a protein that binds target X"),
             ("2", "Build a 3D backbone", "starts from noise, refines into a fold"),
             ("3", "Design the sequence", "which amino acids fit this backbone?"),
             ("4", "Validate in silico", "fold it back: same shape as asked?"),
             ("5", "Make and test", "synthesise gene, express in cells, assay"),
             ("6", "Most fail, a few work", "feed the results into the next round")]
S5_TEXT = [("Nobel Prize 2024", "David Baker, protein design"),
           ("New enzymes", "Reactions nature never evolved"),
           ("Vaccine scaffolds", "Therapeutics already in clinical trials"),
           ("Research tools", "Custom binders: biosensors, reagents")]
S6_TEXT = [("Low success rates", "Wet-lab testing essential"),
           ("Static shapes", "Real proteins move"),
           ("Training-data bias", "Learns only from solved proteins"),
           ("Dual-use risk", "Access limited to verified labs")]
S7_TEXT = ["AI can now design proteins that evolution never produced",
           "Two AI models work together: one designs, one verifies",
           "The lab, not the screen, decides what is real"]


def fill_card(shape, st, i, n):
    kind = st["kind"]
    if kind == "s3" or (kind == "gone" and n == 8) or (kind == "gone" and n == 7):
        h, b = S3_TEXT[i]
        write(shape.text_frame, [dict(runs=[R(h, 24, GREEN, HEAD)], after=4), [R(b, 20, FOREST)]], MSO_ANCHOR.MIDDLE, (0.3, 0.1, 0.3, 0.1))
    elif kind == "node":
        num, h, cap = NODE_TEXT[i]
        hl = (i == 3)
        write(shape.text_frame, [dict(runs=[R(num + "  ", 20, LIME if hl else EMER, HEAD), R(h, 20, WHITE if hl else FOREST, HEAD)], after=3),
                                 [R(cap, 14, WHITE if hl else FOREST)]], MSO_ANCHOR.MIDDLE, (0.18, 0.08, 0.14, 0.08))
    elif kind == "s5":
        h, b = S5_TEXT[i]
        write(shape.text_frame, [dict(runs=[R(h, 22, GREEN, HEAD)], after=2), [R(b, 20, FOREST)]], MSO_ANCHOR.TOP, (0.3, 0.85, 0.25, 0.08))
    elif kind == "s6":
        h, b = S6_TEXT[i]
        write(shape.text_frame, [dict(runs=[R(h, 22, AMBER, HEAD)], after=3), [R(b, 20, FOREST)]], MSO_ANCHOR.TOP, (0.25, 1.0, 0.2, 0.08))
    elif kind == "s7":
        write(shape.text_frame, [[R(str(i + 1) + "\t", 28, GREEN, HEAD), R(S7_TEXT[i], 22, FOREST, HEAD)]], MSO_ANCHOR.MIDDLE, (0.4, 0.08, 0.3, 0.08))
        pPr = shape.text_frame.paragraphs[0]._p.get_or_add_pPr()
        pPr.set("marL", str(Inches(0.65))); pPr.set("indent", str(-Inches(0.65)))
    else:
        write(shape.text_frame, [[R(" ", 20, FOREST)]], MSO_ANCHOR.MIDDLE)


# ---------- speaker notes (rehearsal scripts, signposting from the handout) ----------
NOTES = {
 1: "[~0:10]  Good morning. My name is Linuk. Every protein you've studied so far was made by evolution. Today I'll talk about proteins that weren't.\n\nCUE: Hook. Evolution made every protein you know. Today: ones it didn't.",
 2: "[~0:50]  A protein's sequence determines its 3D shape, and that shape determines its function. Evolution has only tried a tiny fraction of the possible sequences. Most of you have heard of AlphaFold, which predicts the shape of a protein that already exists. The purpose of this presentation is to explain the opposite problem: starting from a shape we want, and working backwards to a sequence that would produce it. That's called de novo protein design.\n\nCUE: Tiny fraction. Prediction vs design. Aim.",
 3: "[~0:50]  Four key terms. De novo means 'from new': a protein that is not derived from any existing one. The backbone is the protein's structural skeleton, without the side chains. A generative model is AI that creates new examples rather than classifying existing ones. The same family of AI that generates images can generate protein shapes: it starts with random noise and gradually refines it into something structured. And a binder is a protein designed to stick tightly to one chosen target molecule.\n\nCUE: De novo. Backbone. Generative model. Binder.\n(If running over: drop the generative model card and define it in one phrase on the next slide.)",
 4: "[~1:50]  As illustrated in this diagram, the process begins when the researcher specifies a goal, for example a protein that binds to one chosen target. Subsequently, the generative model builds a three-dimensional backbone. It works rather like an AI image generator: it starts from random noise and gradually refines it into an ordered, folded shape. Next, a second step decides which amino acid sequence would actually produce that backbone. Now comes the most important step. Before anyone touches a bench, the designed sequence is fed into a structure prediction model, essentially AlphaFold, to check whether it folds back into the shape we asked for. If it doesn't, the design is discarded. Only the survivors are synthesised as genes, expressed in cells, and tested in the lab. Most still fail, and those results feed back into the next round.\n\nCUE: Goal, backbone, sequence, verify, lab, iterate. PAUSE ON THE VERIFY STEP. Point at the diagram.",
 5: "[~1:10]  This technique plays a crucial role in modern biotechnology. In 2024, half the Nobel Prize in Chemistry went to David Baker specifically for computational protein design; the other half went to the AlphaFold team for prediction. Designed proteins are being used as novel enzymes, as vaccine scaffolds, and as research reagents. What's striking is the timeline: this went from barely working to Nobel-recognised within about a decade.\n\nCUE: Nobel 2024. Enzymes. Vaccines. Research tools.\n(If running over: cover only Nobel + enzymes aloud.)",
 6: "[~0:50]  Despite these advantages, several limitations remain. Success rates are still modest: a design that looks perfect on screen often doesn't express or fold in a real cell, so wet-lab validation is essential. Models also tend to produce rigid, idealised structures, whereas real proteins flex and move. And because the same methods that design a useful binder could in principle design a harmful one, access to the most capable systems is increasingly restricted to verified research institutions. That governance question is now part of the science.\n\nCUE: Low success. Rigid shapes. Bias. Dual-use.\n(Never cut this slide: it carries marks for scientific accuracy.)",
 7: "[~0:40]  In conclusion, this advancement has significant implications for molecular biology. We've moved from reading what nature wrote to writing our own. But the computer only proposes; experiments still decide. Thank you, and I'm happy to take questions.\n\nCUE: Design + verify. The lab decides.",
 8: "[~0:10]  Leave this slide up for questions.\n\nQ&A PREP\n- How is this different from AlphaFold? AlphaFold predicts the shape of an existing sequence. Design goes the other way: you start with the shape you want and work out a sequence for it.\n- What's the actual success rate? It varies a lot by target and has improved fast, but most designs still fail. That's why the in-silico filtering step matters: it's cheap to discard a bad design on screen and expensive to discard one at the bench.\n- Could this be misused? Yes, which is why it's an actively governed area and access to the strongest tools is restricted to verified institutions.\n\nCUE: Thank you. Questions.",
}

TITLES = {1: "Designing Proteins That Never Existed", 2: "Introduction and aim", 3: "Key terms", 4: "The de novo design pipeline",
          5: "Why it matters", 6: "Limitations", 7: "Conclusion", 8: "References"}

REFS = [
    [("Dauparas, J., Anishchenko, I., Bennett, N., Bai, H., Ragotte, R. J., Milles, L. F., … Baker, D. (2022). Robust deep learning–based protein sequence design using ProteinMPNN. ", 0),
     ("Science, 378", 1), ("(6615), 49–56. https://doi.org/10.1126/science.add2187", 0)],
    [("Jumper, J., Evans, R., Pritzel, A., Green, T., Figurnov, M., Ronneberger, O., … Hassabis, D. (2021). Highly accurate protein structure prediction with AlphaFold. ", 0),
     ("Nature, 596", 1), ("(7873), 583–589. https://doi.org/10.1038/s41586-021-03819-2", 0)],
    [("The Nobel Prize. (2024, October 9). ", 0), ("Press release: The Nobel Prize in Chemistry 2024", 1),
     (". https://www.nobelprize.org/prizes/chemistry/2024/press-release/", 0)],
    [("Watson, J. L., Juergens, D., Bennett, N. R., Trippe, B. L., Yim, J., Eisenach, H. E., … Baker, D. (2023). De novo design of protein structure and function with RFdiffusion. ", 0),
     ("Nature, 620", 1), ("(7976), 1089–1100. https://doi.org/10.1038/s41586-023-06415-8", 0)],
]

# ---------- Morph transition ----------
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
P159 = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"
MORPH_XML = f"""
<mc:AlternateContent xmlns:mc="{MC}" xmlns:p="{P}">
  <mc:Choice xmlns:p159="{P159}" xmlns:p14="{P14}" Requires="p159">
    <p:transition spd="slow" p14:dur="1200"><p159:morph option="byObject"/></p:transition>
  </mc:Choice>
  <mc:Fallback>
    <p:transition spd="slow"><p:fade/></p:transition>
  </mc:Fallback>
</mc:AlternateContent>
"""


def add_morph(slide):
    sld = slide._element
    node = etree.fromstring(MORPH_XML)
    anchor = sld.find(f"{{{P}}}clrMapOvr")
    if anchor is None:
        anchor = sld.find(f"{{{P}}}cSld")
    anchor.addnext(node)


# ---------- slide builder ----------
TRACK_ACTIVE = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 6}


def build(n):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(BG_WARM if n == 6 else BG)

    # 1) background cast: pictures (same file on every slide)
    a = BLOB_A[n]; b = BLOB_B[n]; hx = HELIX[n]; st = STRAND[n]; al = ALPHA.get(n)
    picture(s, "!!BlobA", "blob_a.png", a[0], a[1], a[2], rot=a[3], alpha=al, alt="Decorative soft green blob")
    picture(s, "!!BlobB", "blob_b.png", b[0], b[1], b[2], rot=b[3], alpha=al, alt="Decorative lime-green blob")
    picture(s, "!!Strand", "strand.png", st[0], st[1], st[2], st[3], st[4], alt="Chain of amino-acid beads on a string")
    picture(s, "!!Helix", "helix.png", hx[0], hx[1], hx[2] / 2, hx[2], hx[3], alt="Stylised green protein alpha-helix ribbon")

    # 2) slide-specific, non-persistent content (plain names; these fade)
    if n == 1:
        textbox(s, "s1_subtitle", 4.7, 4.85, 7.8, 0.95, [[R("How AI Creates New Molecules from Scratch", 26, GREEN, HEAD)]])
        textbox(s, "s1_presenter", 4.6, 6.0, 7.6, 0.9, [dict(runs=[R("Linuk Methsaga Arandara · 25MBB004", 20, FOREST)], after=2),
                                                         [R("IBMBB, University of Colombo", 20, FOREST)]])
    if n == 2:
        textbox(s, "s2_line1", 5.6, 2.05, 10.0, 0.55, [[R("Nature tried only a tiny fraction of possible proteins", 24, FOREST)]], MSO_ANCHOR.MIDDLE)
        textbox(s, "s2_line2", 5.6, 2.7, 10.0, 0.55, [[R("100 residues", 24, FOREST, HEAD), R("  →  20", 24, FOREST), R("100", 24, FOREST, sup=True), R(" possible sequences", 24, FOREST)]], MSO_ANCHOR.MIDDLE)
        c = rounded(s, "s2_card_predict", 0.6 + 2.95, 3.95, 5.9, 1.4, WHITE)
        write(c.text_frame, [dict(runs=[R("Prediction ", 22, GREEN, HEAD), R("(AlphaFold)", 20, FOREST)], after=2), [R("sequence  →  shape", 24, FOREST, HEAD)]], MSO_ANCHOR.MIDDLE, (0.3, 0.1, 0.2, 0.1))
        c = rounded(s, "s2_card_design", 6.83 + 2.95, 3.95, 5.9, 1.4, GREEN)
        write(c.text_frame, [dict(runs=[R("Design ", 22, WHITE, HEAD), R("(this talk)", 20, WHITE)], after=2), [R("desired shape  →  sequence", 24, WHITE, HEAD)]], MSO_ANCHOR.MIDDLE, (0.3, 0.1, 0.2, 0.1))
        rounded(s, "s2_aim_card", 6.67, 5.75, 12.13, 0.95, WHITE)
        chip = rounded(s, "s2_aim_chip", 1.55, 5.75, 1.0, 0.5, LIME, False, 0.2)
        write(chip.text_frame, [[R("AIM", 18, FOREST, HEAD)]], MSO_ANCHOR.MIDDLE, (0, 0, 0, 0), PP_ALIGN.CENTER)
        textbox(s, "s2_aim_text", 7.6, 5.75, 10.2, 0.9, [[R("Explain how AI designs new proteins, and why it matters", 22, FOREST)]], MSO_ANCHOR.MIDDLE)

    # 3) cards / nodes (persistent)
    for i in range(4):
        cs = card_state(n, i)
        sh = rounded(s, f"!!Card{i + 1}", cs["pos"][0], cs["pos"][1], cs["size"][0], cs["size"][1], cs["fill"], cs["shadow"], cs.get("radius", 0.17))
        fill_card(sh, cs, i, n)
    for j, nm in enumerate(("!!Node5", "!!Node6")):
        base = N5 if j == 0 else N6
        pos = base if n == 4 else (15.5, base[1])  # parked well off-slide right unless slide 4
        sh = rounded(s, nm, pos[0], pos[1], NW, NH, MINT if j == 0 else WHITE, n == 4)
        num, h, cap = NODE_TEXT[4 + j]
        write(sh.text_frame, [dict(runs=[R(num + "  ", 20, EMER, HEAD), R(h, 20, FOREST, HEAD)], after=3), [R(cap, 14, FOREST)]], MSO_ANCHOR.MIDDLE, (0.18, 0.08, 0.14, 0.08))

    # 4) arrows (persistent; tiny when not on slide 4)
    for k, (ax, ay, ar) in enumerate(ARROWS):
        arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, 0, 0, 1, 1)
        arrow.name = f"!!Arrow{k + 1}"
        if n == 4:
            place(arrow, ax, ay, 0.38, 0.34, ar)
        else:
            place(arrow, ax, ay, 0.01, 0.01, ar)
        fill(arrow, EMER)
        shadow(arrow, False)

    # 5) overlays
    if n == 4:
        line(s, "s4_iterate_curve", N6[0] - NW / 2, R2Y, NODE_POS[1][0], R1Y + NH / 2 + 0.02, EMER, 2.5, arrow=True, curved=True)
        textbox(s, "s4_iterate_label", 2.95, 4.95, 3.0, 0.4, [[R("feed back, iterate", 14, GREEN, HEAD)]], MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)
        x4, x2 = NODE_POS[3][0], NODE_POS[1][0]
        line(s, "s4_no_up", x4, 2.3, x4, 1.95, AMBER, 2.5)
        line(s, "s4_no_across", x4, 1.95, x2, 1.95, AMBER, 2.5)
        line(s, "s4_no_down", x2, 1.95, x2, 2.28, AMBER, 2.5, arrow=True)
        textbox(s, "s4_no_label", 8.0, 1.66, 4.0, 0.3, [[R("NO: discard the design", 14, AMBER, HEAD)]], MSO_ANCHOR.MIDDLE)
        textbox(s, "s4_yes_label", 12.2, 4.23, 0.8, 0.3, [[R("YES", 14, GREEN, HEAD)]], MSO_ANCHOR.MIDDLE)
    if n == 5:
        for i, kind in enumerate((MSO_SHAPE.STAR_5_POINT, MSO_SHAPE.GEAR_6, MSO_SHAPE.MATH_PLUS, MSO_SHAPE.DONUT)):
            px, py = S5_POS[i]
            glyph(s, f"s5_glyph{i + 1}", kind, px - S5W / 2 + 0.55, py - S5H / 2 + 0.5, 0.58, MINT, GREEN)
    if n == 6:
        for i, (kind, bang) in enumerate(((MSO_SHAPE.DOWN_ARROW, False), (MSO_SHAPE.CUBE, False), (MSO_SHAPE.PIE, False), (MSO_SHAPE.ISOSCELES_TRIANGLE, True))):
            px, py = S6_POS[i]
            glyph(s, f"s6_glyph{i + 1}", kind, px - S6W / 2 + 0.7, py - S6H / 2 + 0.65, 0.78, AMBER_PALE, AMBER, bang)
    if n == 8:
        refs = textbox(s, "s8_refs", 6.65, 3.55, 12.1, 3.6, [], MSO_ANCHOR.TOP)
        tf = refs.text_frame
        tf.word_wrap = True
        first = True
        for ref in REFS:
            para = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            para.space_after = Pt(12)
            pPr = para._p.get_or_add_pPr()
            pPr.set("marL", str(Inches(0.5))); pPr.set("indent", str(-Inches(0.5)))  # APA hanging indent
            for text, it in ref:
                run = para.add_run(); run.text = text
                run.font.size, run.font.name, run.font.italic = Pt(14), BODY, bool(it)
                run.font.color.rgb = rgb(FOREST)

    if n == 8:
        rounded(s, "s8_peer_card", 6.67, 4.85, 12.13, 0.7, WHITE)
        textbox(s, "s8_peer_text", 6.67, 4.85, 11.6, 0.7, [[R("Peer-reviewed: ", 16, GREEN, HEAD), R("Watson et al. (2023) \u00b7 Dauparas et al. (2022) \u00b7 Jumper et al. (2021)", 16, FOREST)]], MSO_ANCHOR.MIDDLE)

    # 6) trackers (persistent progress dots)
    act = TRACK_ACTIVE.get(n)
    for k in range(1, 7):
        cx = 6.67 + (k - 3.5) * 0.5
        cy = 6.85 if n > 1 else 8.0
        d = 0.28 if act == k else 0.16
        dot = s.shapes.add_shape(MSO_SHAPE.OVAL, 0, 0, 1, 1)
        dot.name = f"!!Tracker{k}"
        place(dot, cx, cy, d, d)
        fill(dot, GREEN if act == k else MINT)
        shadow(dot, False)

    # 7) title + slide number (persistent text)
    if n == 1:
        textbox(s, "!!Title", 0.8 + 3.8, 2.0 + 1.1, 7.6, 2.2, [[R(TITLES[1], 44, FOREST, HEAD)]], MSO_ANCHOR.TOP)
    else:
        textbox(s, "!!Title", 0.6 + 5.0, 0.55 + 0.475, 10.0, 0.95, [[R(TITLES[n], 36, FOREST, HEAD)]], MSO_ANCHOR.MIDDLE)
    textbox(s, "!!SlideNum", 12.65, 7.17 if n > 1 else 8.2, 0.6, 0.3, [[R(str(n), 14, FOREST)]], MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT)

    # 8) notes + transition
    s.notes_slide.notes_text_frame.text = NOTES[n]
    if n >= 2:
        add_morph(s)

    names = [sh.name for sh in s.shapes]
    assert len(names) == len(set(names)), f"duplicate shape names on slide {n}: {[x for x in names if names.count(x) > 1]}"
    return s


for i in range(1, 9):
    build(i)
prs.core_properties.title = "Designing Proteins That Never Existed"
prs.core_properties.author = "Linuk Methsaga Arandara"
prs.save(OUT)
print("saved", os.path.abspath(OUT))
