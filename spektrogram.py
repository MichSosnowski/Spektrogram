######################################
#   Cyfrowe Przetwarzanie Sygnałów   #
#            2020/2021               #
#           Spektrogram              #
#      Autor: Michał Sosnowski       #
######################################

from tkinter import *
from tkinter import filedialog, messagebox
from tkinter import ttk
import warnings
import soundfile as sf
import sounddevice as sd
from scipy.signal import windows
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
from matplotlib.ticker import FuncFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageColor
import queue
import os
import tempfile
import win32api
import win32print
matplotlib.use('TKAgg')

# klasa ToolTip tworząca dymki informacyjne wyświetlane
# po najechaniu kursorem myszki na widgety GUI;
# kod klasy pochodzi ze strony:
# http://www.voidspace.org.uk/python/weblog/arch_d7_2006_07_01.shtml

class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 37
        y = y + self.widget.winfo_rooty() + 27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(tw, text = self.text, justify = LEFT, background = "#ffffe0", relief = SOLID, borderwidth = 1, font = ("Tahoma", "8", "normal"))
        label.pack(ipadx = 1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def setToolTip(widget, text):
    toolTip = ToolTip(widget)
    def enter(event):
        toolTip.showtip(text)
    def leave(event):
        toolTip.hidetip()
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)
    return toolTip

title = "Spektrogram - Bez tytułu 1"                            # przechowuje tytuł okna programu
opcja = 0                                                       # przechowuje informację o tym, czy pokazywać informację o wyborze sposobu przybliżania w trakcie tej sesji
opcja2 = 0                                                      # przechowuje informację o tym, czy pokazywać informację o wyborze sposobu odtwarzania w trakcie tej sesji
warnings.filterwarnings("ignore", category = UserWarning)
warnings.filterwarnings("ignore", category = RuntimeWarning)

# klasa Aplikacja odpowiedzialna jest za utworzenie
# graficznego interfejsu użytkownika w programie

class Aplikacja(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent

        # ikony używane w GUI
        self.ikonka = PhotoImage(file = "gui\\open.png")
        self.ikonka2 = PhotoImage(file = "gui\\save.png")
        self.ikonka3 = PhotoImage(file = "gui\\saveas.png")
        self.ikonka4 = PhotoImage(file = "gui\\printer.png")
        self.ikonka5 = PhotoImage(file = "gui\\close.png")
        self.ikonka6 = PhotoImage(file = "gui\\tick.png")
        self.ikonka7 = PhotoImage(file = "gui\\microphone2.png")
        self.ikonka8 = PhotoImage(file = "gui\\magnifier+1.png")
        self.ikonka9 = PhotoImage(file = "gui\\magnifier-1.png")

        # pasek menu programu
        menubar = Menu(self.parent)

        # menu Plik na pasku menu
        self.filemenu = Menu(menubar, tearoff = 0)
        self.filemenu.add_command(label = " Nagraj...", accelerator = "Ctrl+R", compound = "left", image = self.ikonka7, command = self.nagraj_dialog)
        self.parent.bind("<Control-r>", lambda event: self.nagraj_dialog())
        self.filemenu.add_separator()
        self.filemenu.add_command(label = "Otwórz...", accelerator = "Ctrl+O", compound = "left", image = self.ikonka, command = self.otworz)
        self.parent.bind("<Control-o>", lambda event: self.otworz())
        self.filemenu.add_separator()
        self.filemenu.add_command(label = "Zapisz", accelerator = "Ctrl+S", compound = "left", image = self.ikonka2, command = self.zapisz)
        self.parent.bind("<Control-s>", lambda event: self.zapisz())
        self.filemenu.add_command(label = "Zapisz jako...", compound = "left", image = self.ikonka3, command = self.zapisz_jako)
        self.filemenu.add_separator()
        self.filemenu.add_command(label = "Drukuj...", accelerator = "Ctrl+P", compound = "left", image = self.ikonka4, command = self.drukuj)
        self.filemenu.add_separator()
        self.filemenu.add_command(label = "Zamknij", accelerator = "Alt+F4", compound = "left", image = self.ikonka5, command = zamknij)
        menubar.add_cascade(label = "Plik", menu = self.filemenu)

        # menu Edycja na pasku menu
        self.editmenu = Menu(menubar, tearoff = 0)
        self.editmenu.add_command(label = "Skala logarytmiczna", compound = "right", command = self.zmien_skale)
        self.editmenu.add_command(label = "Skala liniowa", compound = "right", command = self.zmien_skale)
        self.editmenu.add_separator()
        self.editmenu.add_command(label = "Zmień długość zakładki...", command = self.zmien_zakladke)
        menubar.add_cascade(label = "Edycja", menu = self.editmenu)

        # menu Wyświetlacz na pasku menu
        self.displaymenu = Menu(menubar, tearoff = 0)
        self.displaymenu.add_command(label = "Przybliż", compound = "left", image = self.ikonka8, command = self.przybliz)
        self.displaymenu.add_command(label = "Oddal (100%)", compound = "left", image = self.ikonka9, command = self.oddal)
        menubar.add_cascade(label = "Wyświetlacz", menu = self.displaymenu)

        # menu Widok na pasku menu
        self.viewmenu = Menu(menubar, tearoff = 0)
        self.viewmenu.add_command(label = "Spektrogram podstawowy", compound = "right", command = self.stworz_podstawowy)
        self.viewmenu.add_command(label = "Spektrogram wąskopasmowy", compound = "right", command = self.stworz_waskopasmowy)
        self.viewmenu.add_command(label = "Spektrogram szerokopasmowy", compound = "right", command = self.stworz_szerokopasmowy)
        self.viewmenu.add_separator()
        self.viewmenu.add_command(label = "Okno Hanna", compound = "right", command = lambda: self.ustaw_okno(4))
        self.viewmenu.add_command(label = "Okno trójkątne", compound = "right", command = lambda: self.ustaw_okno(5))
        self.viewmenu.add_command(label = "Okno prostokątne", compound = "right", command = lambda: self.ustaw_okno(6))
        self.viewmenu.add_command(label = "Okno Bartletta", compound = "right", command = lambda: self.ustaw_okno(7))
        self.viewmenu.add_command(label = "Okno Hamminga", compound = "right", command = lambda: self.ustaw_okno(8))
        self.viewmenu.add_command(label = "Okno Blackmana", compound = "right", command = lambda: self.ustaw_okno(9))
        menubar.add_cascade(label = "Widok", menu = self.viewmenu)

        # konfiguracja opcji dostępnych w poszczególnych zakładkach paska menu
        self.filemenu.entryconfig(4, state = DISABLED)
        self.filemenu.entryconfig(5, state = DISABLED)
        self.filemenu.entryconfig(7, state = DISABLED)

        self.editmenu.entryconfig(0, state = DISABLED)
        self.editmenu.entryconfig(1, state = DISABLED)
        self.editmenu.entryconfig(3, state = DISABLED)

        self.displaymenu.entryconfig(0, state = DISABLED)
        self.displaymenu.entryconfig(1, state = DISABLED)

        self.viewmenu.entryconfig(0, state = DISABLED)
        self.viewmenu.entryconfig(1, state = DISABLED)
        self.viewmenu.entryconfig(2, state = DISABLED)
        self.viewmenu.entryconfig(4, state = DISABLED)
        self.viewmenu.entryconfig(5, state = DISABLED)
        self.viewmenu.entryconfig(6, state = DISABLED)
        self.viewmenu.entryconfig(7, state = DISABLED)
        self.viewmenu.entryconfig(8, state = DISABLED)
        self.viewmenu.entryconfig(9, state = DISABLED)

        self.parent.config(menu = menubar)

        global filename
        global directory
        filename = ""
        self.file = ""
        directory = tempfile.TemporaryDirectory()

        # wybiera sposób zapisu w zależności od nazwy okna programu przypisany do przycisku zapisz na pasku narzędzi
        def zapisz():
            if title == "Spektrogram - Bez tytułu 1*":
                self.zapisz_jako()
                if filename == "":
                    return
            else:
                self.zapisz()

        # pozostałe ikony używane przez GUI programu wraz z przyciskami na pasku narzędzi
        self.photo = PhotoImage(file = "gui\\play.png")
        self.button = Button(image = self.photo, cursor = "hand2", state = DISABLED, command = self.odtworz)
        self.button.place(x = 74, y = 0)
        setToolTip(self.button, text = "Odtwórz")

        self.photo2 = PhotoImage(file = "gui\\stop.png")
        self.button2 = Button(image = self.photo2, cursor = "hand2", state = DISABLED, command = self.zatrzymaj)
        self.button2.place(x = 110, y = 0)
        setToolTip(self.button2, text = "Zatrzymaj odtwarzanie")

        self.photo6 = PhotoImage(file = "gui\\magnifier+.png")
        self.button7 = Button(image = self.photo6, cursor = "hand2", state = DISABLED, command = self.przybliz)
        self.button7.place(x = 147, y = 0)
        setToolTip(self.button7, text = "Przybliż")

        self.photo7 = PhotoImage(file = "gui\\magnifier-.png")
        self.button8 = Button(image = self.photo7, cursor = "hand2", state = DISABLED, command = self.oddal)
        self.button8.place(x = 184, y = 0)
        setToolTip(self.button8, text = "Oddal (100%)")

        self.photo8 = PhotoImage(file = "gui\\open2.png")
        self.button9 = Button(image = self.photo8, cursor = "hand2", command = self.otworz)
        self.button9.place(x = 0, y = 0)
        setToolTip(self.button9, text = "Otwórz...")

        self.photo9 = PhotoImage(file = "gui\\save2.png")
        self.button10 = Button(image = self.photo9, cursor = "hand2", state = DISABLED, command = zapisz)
        self.button10.place(x = 37, y = 0)
        setToolTip(self.button10, text = "Zapisz...")

        self.photo10 = PhotoImage(file = "gui\\triangle.png")
        self.button12 = Button(image = self.photo10, cursor = "hand2", state = DISABLED, command = lambda: self.ustaw_okno(5))
        self.button12.place(x = 221, y = 0)
        setToolTip(self.button12, text = "Okno trójkątne")

        self.photo11 = PhotoImage(file = "gui\\bartlett.png")
        self.button13 = Button(image = self.photo11, cursor = "hand2", state = DISABLED, command = lambda: self.ustaw_okno(7))
        self.button13.place(x = 258, y = 0)
        setToolTip(self.button13, text = "Okno Bartletta")

        self.photo12 = PhotoImage(file = "gui\\hamming.png")
        self.button14 = Button(image = self.photo12, cursor = "hand2", state = DISABLED, command = lambda: self.ustaw_okno(8))
        self.button14.place(x = 295, y = 0)
        setToolTip(self.button14, text = "Okno Hamminga")

        # figura przygotowana na prezentację spektrogramu
        self.fig = Figure(tight_layout = True, facecolor = "#f0f0f0")
        self.spektrogram = self.fig.add_subplot(111)
        self.spektrogram.plot([])
        self.spektrogram.xaxis.set_visible(False)
        self.spektrogram.yaxis.set_visible(False)

        self.wykres = FigureCanvasTkAgg(self.fig, master = self.parent)
        self.wykres.get_tk_widget().place(x = 98, y = 40, width = 1000)
        self.wykres.draw()

        # figura przygotowana na prezentację wykresu amplitudy możliwej do edycji (przybliżanie/oddalanie)
        self.fig2 = Figure(figsize = [1, 1.2], tight_layout = True, facecolor = "#f0f0f0")
        self.amplituda = self.fig2.add_subplot(111)
        self.amplituda.plot([])
        self.amplituda.xaxis.set_visible(False)
        self.amplituda.yaxis.set_visible(False)

        self.wykres2 = FigureCanvasTkAgg(self.fig2, master = self.parent)
        self.wykres2.get_tk_widget().place(x = 98, y = 530, width = 1000)
        self.wykres2.draw()

        # figura przygotowana na prezentację wykresu amplitudy
        self.fig3 = Figure(figsize = [1, 1.2], tight_layout = True, facecolor = "#f0f0f0")
        self.widmo = self.fig3.add_subplot(111)
        self.widmo.plot([])
        self.widmo.xaxis.set_visible(False)
        self.widmo.yaxis.set_visible(False)

        self.wykres3 = FigureCanvasTkAgg(self.fig3, master = self.parent)
        self.wykres3.get_tk_widget().place(x = 98, y = 635, width = 1000)
        self.wykres3.draw()

        # pasek prezentujący kolory wykorzystywane na spektrogramie (legenda kolorów)
        self.fig4 = Figure(facecolor = "#f0f0f0")
        self.pasek = self.fig4.add_subplot(9, 9, (9, 9))
        colors = plt.get_cmap('viridis')
        osie = self.fig4.add_axes([0.1, 0.37, 0.87, 0.63])
        bar = self.fig4.colorbar(mappable = cm.ScalarMappable(cmap = colors), orientation = "horizontal", cax = osie)
        bar.set_ticks([])
        self.pasek = FigureCanvasTkAgg(self.fig4, master = self.parent)

        # kanwa przygotowana pod informacje na temat zakładek i długości okien
        self.kanwa = Canvas(self.parent, width = 100, height = 75)
        self.kanwa.place(x = 0, y = 555, width = 80)

        # kanwa przygotowana pod informacje na temat punktu znajdującego się pod kursorem myszy na spektrogramie
        self.kanwa2 = Canvas(self.parent, width = 100, height = 75)
        self.kanwa2.place(x = 1100, y = 555, width = 80)

    # odczytuje informacje na temat położenia punktu na spektrogramie
    def odczytaj_punkt(self, event):
        if not event.inaxes:
            return

        x, y = event.xdata, event.ydata
        self.kanwa2.delete('all')
        self.info2 = self.kanwa2.create_text(8, 20, text = "F: ", font = "Times 11")
        self.info2 = self.kanwa2.create_text(46, 20, text = "%1.0f Hz" % y, font = "Times 11")
        self.info2 = self.kanwa2.create_text(9, 40, text = "T: ", font = "Times 11")
        self.info2 = self.kanwa2.create_text(47, 40, text = "%1.2f s" % x, font = "Times 11")

    # informuje o tym, że przycisk został naciśnięty
    def isClicked(self):
        self.stan = 1

    # pauzuje nagrywanie pliku dźwiękowego
    def isPause(self):
        self.stan = -1

    # wznawia nagrywanie pliku dźwiękowego
    def isRecord(self):
        self.stan = 0

    # wyświetla okno dialogowe nagrywania pliku dźwiękowego
    def nagraj_dialog(self):
        plik = self.file

        self.top = Toplevel()
        self.top.title("Nagraj...")
        self.top.resizable(False, False)
        self.top.focus_set()
        self.top.grab_set()
        szer = self.top.winfo_screenwidth()
        wys = self.top.winfo_screenheight()
        x = int((szer - 450) / 2)
        y = int((wys - 260) / 3)
        self.top.geometry("450x260+{0}+{1}".format(x, y))

        self.stan = 0

        # kolejne ikony wykorzystywane przez program na przyciskach w oknie dialogowym nagrywania
        self.photo3 = PhotoImage(file = "gui\\microphone.png")
        self.photo4 = PhotoImage(file = "gui\\trash.png")

        label = Label(self.top, font = ("TimesNewRoman", "10"), text = "Wykryty mikrofon:")
        label.place(bordermode = OUTSIDE, x = 10, y = 30)
        self.lista_urzadzen = sd.query_devices(kind = 'input')
        if len(self.lista_urzadzen["name"]) > 30:
            self.urzadzenie = self.lista_urzadzen["name"][:20] + "..."
        else:
            self.urzadzenie = self.lista_urzadzen["name"]
        self.label2 = Label(self.top, font = ("TimesNewRoman", "10"), text = self.urzadzenie)
        self.label2.place(bordermode = OUTSIDE, x = 220, y = 30)
        setToolTip(self.label2, text = "Jeśli chcesz zmienić mikrofon na inny,\nustaw wybrany mikrofon na domyślny\nw Twoim systemie operacyjnym\ni zrestartuj aplikację.")

        label3 = Label(self.top, font = ("TimesNewRoman", "10"), text = "Częstotliwość próbkowania:")
        label3.place(bordermode = OUTSIDE, x = 10, y = 75)
        self.temp2 = StringVar()
        option = ttk.Combobox(self.top, textvariable = self.temp2, state = 'readonly', justify = RIGHT, width = 30)
        option['values'] = ("Domyślna", "8000", "11025", "16000", "22050", "32000", "44100", "48000", "88200", "96000", "192000")
        option.current(0)
        option.place(bordermode = OUTSIDE, x = 220, y = 76)
        option.bind("<<ComboboxSelected>>", lambda event: label.focus())

        label4 = Label(self.top, font = ("TimesNewRoman", "10"), text = "Kanały:")
        label4.place(bordermode = OUTSIDE, x = 10, y = 120)
        self.temp3 = StringVar()
        option2 = ttk.Combobox(self.top, textvariable = self.temp3, state = 'readonly', justify = RIGHT, width = 30)
        if self.lista_urzadzen["max_input_channels"] == 1:
            option2['values'] = ("Mono")
        else:
            option2['values'] = ("Mono", "Stereo")
        option2.current(0)
        option2.place(bordermode = OUTSIDE, x = 220, y = 124)
        option2.bind("<<ComboboxSelected>>", lambda event: label.focus())

        self.button3 = Button(self.top, width = 30, height = 30, image = self.photo3, cursor = "hand2", command = self.nagraj)
        self.button3.place(bordermode = OUTSIDE, x = 115, y = 170)
        setToolTip(self.button3, text = "Nagrywaj")
        self.button4 = Button(self.top, width = 30, height = 30, state = DISABLED, image = self.photo2, cursor = "hand2", command = self.isClicked)
        self.button4.place(bordermode = OUTSIDE, x = 160, y = 170)
        setToolTip(self.button4, text = "Zatrzymaj nagrywanie")
        self.button5 = Button(self.top, width = 30, height = 30, state = DISABLED, image = self.photo, cursor = "hand2", command = lambda: self.odtworz_dzwiek(self.file, 1))
        self.button5.place(bordermode = OUTSIDE, x = 205, y = 170)
        setToolTip(self.button5, text = "Odtwórz nagrany dźwięk")
        self.button11 = Button(self.top, width = 30, height = 30, state = DISABLED, image = self.photo2, cursor = "hand2", command = self.zatrzymaj)
        self.button11.place(bordermode = OUTSIDE, x = 250, y = 170)
        setToolTip(self.button11, text = "Zatrzymaj odtwarzanie")
        self.button6 = Button(self.top, width = 30, height = 30, state = DISABLED, image = self.photo4, cursor = "hand2", command = self.usun_plik)
        self.button6.place(bordermode = OUTSIDE, x = 295, y = 170)
        setToolTip(self.button6, text = "Usuń nagrany plik")

        # zamyka okno dialogowe nagrywania pliku po anulowaniu nagrania (przez naciśnięcie X)
        def zamknij():
            sd.stop()
            self.file = plik
            self.top.destroy()

        # zamyka okno dialogowe nagrywania pliku po jego nagraniu (przez naciśnięcie przycisku Utwórz wykresy)
        def zamknij_top():
            sd.stop()
            if self.file != "" and self.file != plik:
                self.window = "hann"
                self.skala = 'dB'
                self.nfft = 1024
                self.noverlap = 512
                self.typ = 0
                self.utworz_wykresy()
                self.filemenu.entryconfig(5, state = ACTIVE)
                self.filemenu.entryconfig(7, state = ACTIVE)
                self.parent.bind("<Control-p>", lambda event: self.drukuj())
                self.editmenu.entryconfig(0, state = DISABLED, image = self.ikonka6)
                self.editmenu.entryconfig(1, state = ACTIVE, image = "")
                self.editmenu.entryconfig(3, state = ACTIVE)
                self.displaymenu.entryconfig(0, state = ACTIVE)
                self.displaymenu.entryconfig(1, state = ACTIVE)
                self.viewmenu.entryconfig(0, state = DISABLED, image = self.ikonka6)
                self.viewmenu.entryconfig(1, state = ACTIVE, image = "")
                self.viewmenu.entryconfig(2, state = ACTIVE, image = "")
                self.viewmenu.entryconfig(4, state = DISABLED, image = self.ikonka6)
                self.viewmenu.entryconfig(5, state = ACTIVE, image = "")
                self.viewmenu.entryconfig(6, state = ACTIVE, image = "")
                self.viewmenu.entryconfig(7, state = ACTIVE, image = "")
                self.viewmenu.entryconfig(8, state = ACTIVE, image = "")
                self.viewmenu.entryconfig(9, state = ACTIVE, image = "")
                self.button.config(state = NORMAL)
                self.button.update()
                self.button2.config(state = NORMAL)
                self.button2.update()
                self.button7.config(state = NORMAL)
                self.button7.update()
                self.button8.config(state = NORMAL)
                self.button8.update()
                self.button10.config(state = NORMAL)
                self.button10.update()
                self.button12.config(state = NORMAL)
                self.button12.update()
                self.button13.config(state = NORMAL)
                self.button13.update()
                self.button14.config(state = NORMAL)
                self.button14.update()
                global title
                if title[len(title) - 1] != '*':
                    title += '*'
                    self.parent.title(title)
            self.top.destroy()

        self.top.protocol("WM_DELETE_WINDOW", zamknij)
        self.button15 = Button(self.top, width = 20, height = 1, text = "Utwórz wykresy", state = DISABLED, cursor = "hand2", command = zamknij_top)
        self.button15.place(bordermode = OUTSIDE, x = 148, y = 220)
        setToolTip(self.button15, text = "Tworzy wykresy na podstawie nagranego pliku")

    # metoda wykonywana podczas zapisu danych audio do pliku
    def callback(self, indata, frames, time, status):
        if self.stan == -1 or self.stan == -3:
            return
        q.put(indata.copy())

    # nagrywa plik dźwiękowy z wybranymi przez użytkownika opcjami w oknie dialogowym nagrywania dźwięku
    def nagraj(self):
        plik = self.file

        self.button4.config(state = NORMAL)
        self.button4.update()
        self.button5.config(state = DISABLED)
        self.button5.update()
        self.button6.config(state = DISABLED)
        self.button6.update()
        self.button11.config(state = DISABLED)
        self.button11.update()

        if self.temp2.get() == "Domyślna":
            self.fs = int(self.lista_urzadzen["default_samplerate"])
        else:
            self.fs = int(self.temp2.get())

        if self.temp3.get() == "Mono":
            self.kan = 1
        else:
            self.kan = 2

        ext = ""
        while ext != ".wav":
            self.file = filedialog.asksaveasfilename(filetypes = [("WAV (*.wav)", "*.wav")], defaultextension = "*.wav", title = "Zapisz nagranie jako...")
            temp, ext = os.path.splitext(self.file)
            if self.file == "":
                self.file = plik
                self.button3.config(relief = RAISED)
                self.button3.update()
                self.button4.config(state = DISABLED)
                self.button4.update()
                return
            if ext != ".wav":
                messagebox.showerror("Nieprawidłowe rozszerzenie pliku", "Nieprawidłowe rozszerzenie dla pliku dźwiękowego.\nPodaj nazwę pliku ponownie.")

        self.photo5 = PhotoImage(file = "gui\\pause.png")
        tool = setToolTip(self.button3, text = "Pauza")

        sd.stop()

        # nagrywa plik dźwiękowy bez ustalonego okresu czasowego
        global q
        q = queue.Queue()
        with sf.SoundFile(self.file, mode = 'w', samplerate = self.fs, channels = self.kan) as plik:
            with sd.InputStream(samplerate = self.fs, channels = self.kan, callback = self.callback):
                while self.stan != 1:
                    if self.stan == 0:
                        self.button3.config(image = self.photo5, command = self.isPause)
                        tool.hidetip()
                        tool = setToolTip(self.button3, text = "Pauza")
                        self.stan -= 2
                    elif self.stan == -1:
                        self.button3.config(image = self.photo, command = self.isRecord)
                        tool.hidetip()
                        tool = setToolTip(self.button3, text = "Wznów nagranie")
                        self.button3.update()
                        while q.empty() is False:
                            plik.write(q.get())
                        self.stan -= 2
                        continue
                    elif self.stan == -3:
                        self.button3.update()
                        continue
                    plik.write(q.get())
                    self.button3.update()
                    self.button4.update()

        while q.empty() is False:
            plik.write(q.get())
        self.stan = 0

        self.button3.config(image = self.photo3, command = self.nagraj)
        setToolTip(self.button3, text = "Nagrywaj")
        self.button3.update()
        self.button4.config(state = DISABLED)
        self.button4.update()
        self.button5.config(state = NORMAL)
        self.button5.update()
        self.button6.config(state = NORMAL)
        self.button6.update()
        self.button11.config(state = NORMAL)
        self.button11.update()
        self.button15.config(state = NORMAL)
        self.button15.update()

    # wyświetla informacje na temat sposobu odtworzenia pliku dźwiękowego
    def odtworz(self):
        top3 = Toplevel()
        top3.title("Odtwórz dźwięk...")
        top3.resizable(False, False)
        top3.focus_force()
        top3.grab_set()
        szer = top3.winfo_screenwidth()
        wys = top3.winfo_screenheight()
        x = int((szer - 460) / 2)
        y = int((wys - 145) / 3)
        top3.geometry("460x145+{0}+{1}".format(x, y))

        label = Label(top3, image = "::tk::icons::information")
        label.place(bordermode = OUTSIDE, x = 15, y = 20)

        etykieta = Label(top3, font = ("TimesNewRoman", "10"), text = "Jak chcesz odtworzyć dźwięk?")
        etykieta.place(bordermode = OUTSIDE, x = 65, y = 20)

        temp = IntVar()
        radio = Radiobutton(top3, text = "Odtwórz cały dźwięk", variable = temp, value = 2)
        radio.place(bordermode = OUTSIDE, x = 45, y = 60)
        radio.select()
        radio2 = Radiobutton(top3, text = "Wybierz przedział czasowy do odtworzenia", variable = temp, value = 3)
        radio2.place(bordermode = OUTSIDE, x = 195, y = 60)
        radio2.deselect()

        # wykonuje akcję w zależności od wybranej opcji odtwarzania dźwięku
        def wykonaj_akcje(wybor):
            top3.destroy()
            if wybor == 2:
                self.odtworz_dzwiek(self.file, 0)
            else:
                self.span2 = SpanSelector(self.spektrogram, self.dziel_plik, 'horizontal', useblit = True, rectprops = dict(alpha = 0.5, facecolor = 'red'))
                self.wyswietl_informacje()

        przycisk = Button(top3, width = 12, height = 1, text = "OK", cursor = "hand2", command = lambda: wykonaj_akcje(temp.get()))
        przycisk.place(bordermode = OUTSIDE, x = 245, y = 100)
        przycisk2 = Button(top3, width = 12, height = 1, text = "Anuluj", cursor = "hand2", command = top3.destroy)
        przycisk2.place(bordermode = OUTSIDE, x = 345, y = 100)

    # informuje o sposobie wybrania określonej części pliku dźwiękowego do odtworzenia
    def wyswietl_informacje(self):
        global opcja2

        if opcja2 == 0:
            def nie_zamykaj():
                pass

            def zmien(decyzja):
                global opcja2
                opcja2 = decyzja

            top5 = Toplevel()
            top5.title("Wybierz przedział czasowy do odtworzenia")
            top5.protocol("WM_DELETE_WINDOW", nie_zamykaj)
            top5.resizable(False, False)
            top5.focus_force()
            top5.grab_set()
            szer = top5.winfo_screenwidth()
            wys = top5.winfo_screenheight()
            x = int((szer - 450) / 2)
            y = int((wys - 140) / 3)
            top5.geometry("450x140+{0}+{1}".format(x, y))

            label = Label(top5, image = "::tk::icons::information")
            label.place(bordermode = OUTSIDE, x = 15, y = 20)

            etykieta = Label(top5, font = ("TimesNewRoman", "10"), text = "W celu wybrania przedziału do odtworzenia\nzaznacz lewym przyciskiem myszy obszar na spektrogramie.")
            etykieta.place(bordermode = OUTSIDE, x = 55, y = 20)

            przycisk = Button(top5, width = 12, height = 1, text = "OK", cursor = "hand2", command = top5.destroy)
            przycisk.place(bordermode = OUTSIDE, x = 340, y = 100)

            decyzja = IntVar()
            check = ttk.Checkbutton(top5, text = "Nie pokazuj tej podpowiedzi więcej w trakcie tej sesji.", variable = decyzja, cursor = "hand2", command = lambda: zmien(decyzja.get()))
            check.place(bordermode = OUTSIDE, x = 15, y = 100)

    # dzieli plik zgodnie z wybranym przedziałem czasu
    def dziel_plik(self, xmin, xmax):
        global directory
        data, fs = sf.read(self.file)
        kawalek = data[int(xmin * fs) : int(xmax * fs)]
        nazwa = tempfile.NamedTemporaryFile(suffix = ".wav", dir = directory.name, delete = False)
        sf.write(nazwa.name, kawalek, fs)
        self.odtworz_dzwiek(nazwa.name, 0)
        del self.span2

    # odtwarza dźwięk z nagranego bądź wczytanego pliku dźwiękowego z uwzględnieniem przedziału czasowego albo w całości
    def odtworz_dzwiek(self, file, ster):
        if file == "":
            return
        if os.path.isfile(file) is False:
            messagebox.showerror("Brak pliku", "Plik nie istnieje.\nNie można odtworzyć dźwięku.")
            if ster == 1:
                self.button5.config(state = DISABLED)
                self.button5.update()
                self.button6.config(state = DISABLED)
                self.button6.update()
                self.button11.config(state = DISABLED)
                self.button11.update()
            else:
                self.button.config(state = DISABLED)
                self.button.update()
                self.button2.config(state = DISABLED)
                self.button2.update()
            self.file = ""
            return
        data, fs = sf.read(file)
        sd.play(data, fs)

    # zatrzymuje odtwarzanie dźwięku
    def zatrzymaj(self):
        sd.stop()

    # usuwa plik po jego nagraniu w oknie dialogowym nagrywania w przypadku takiej decyzji użytkownika
    def usun_plik(self):
        if os.path.isfile(self.file) is False:
            messagebox.showerror("Brak pliku", "Plik nie istnieje lub został już wcześniej usunięty.")
            self.button5.config(state = DISABLED)
            self.button5.update()
            self.button6.config(state = DISABLED)
            self.button6.update()
            self.button11.config(state = DISABLED)
            self.button11.update()
            self.file = ""
            return
        if messagebox.askokcancel("Usuwanie nagrania", "Czy na pewno chcesz usunąć plik " + os.path.basename(self.file) + "?") is True:
            os.remove(self.file)
            self.button5.config(state = DISABLED)
            self.button5.update()
            self.button6.config(state = DISABLED)
            self.button6.update()
            self.button11.config(state = DISABLED)
            self.button11.update()
            self.file = ""

    # otwiera i wczytuje plik dźwiękowy wybrany przez użytkownika programu
    def otworz(self):
        global title
        plik = self.file
        ext = ""
        while ext != ".wav":
            self.file = filedialog.askopenfilename(title = "Otwórz plik...", filetypes = [("WAV (*wav)", "*.wav")])
            temp, ext = os.path.splitext(self.file)
            if self.file == "":
                self.file = plik
                return
            if ext != ".wav":
                messagebox.showerror("Nieprawidłowe rozszerzenie pliku", "Nieprawidłowe rozszerzenie dla pliku dźwiękowego.\nPodaj nazwę pliku ponownie.")
        sd.stop()
        self.window = "hann"
        self.skala = 'dB'
        self.nfft = 1024
        self.noverlap = 512
        self.typ = 0
        self.utworz_wykresy()
        self.filemenu.entryconfig(5, state = ACTIVE)
        self.filemenu.entryconfig(7, state = ACTIVE)
        self.parent.bind("<Control-p>", lambda event: self.drukuj())
        self.editmenu.entryconfig(0, state = DISABLED, image = self.ikonka6)
        self.editmenu.entryconfig(1, state = ACTIVE, image = "")
        self.editmenu.entryconfig(3, state = ACTIVE)
        self.displaymenu.entryconfig(0, state = ACTIVE)
        self.displaymenu.entryconfig(1, state = ACTIVE)
        self.viewmenu.entryconfig(0, state = DISABLED, image = self.ikonka6)
        self.viewmenu.entryconfig(1, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(2, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(4, state = DISABLED, image = self.ikonka6)
        self.viewmenu.entryconfig(5, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(6, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(7, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(8, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(9, state = ACTIVE, image = "")
        self.button.config(state = NORMAL)
        self.button.update()
        self.button2.config(state = NORMAL)
        self.button2.update()
        self.button7.config(state = NORMAL)
        self.button7.update()
        self.button8.config(state = NORMAL)
        self.button8.update()
        self.button10.config(state = NORMAL)
        self.button10.update()
        self.button12.config(state = NORMAL)
        self.button12.update()
        self.button13.config(state = NORMAL)
        self.button13.update()
        self.button14.config(state = NORMAL)
        self.button14.update()
        if title[len(title) - 1] != '*':
            title += '*'
            self.parent.title(title)

    # zapisuje wynik programu zawierający spektrogram i amplitudę po raz pierwszy
    def zapisz_jako(self):
        global title
        global filename
        plik = filename

        ext = ""
        while ext != ".png" and ext != ".jpg":
            filename = filedialog.asksaveasfilename(title = "Zapisz jako...", filetypes = [("PNG (*.png)", "*.png"), ("JPG (*.jpg)", "*.jpg")], defaultextension = "*.png")
            temp, ext = os.path.splitext(filename)
            if filename == "" and plik != "":
                filename = plik
                return
            elif filename == "":
                return
            if ext != ".png" and ext != ".jpg":
                messagebox.showerror("Nieobsługiwane rozszerzenie pliku", "Nieobsługiwane rozszerzenie dla pliku graficznego.\nPodaj nazwę pliku ponownie.")

        title = "Spektrogram - " + str(os.path.basename(filename))
        self.parent.title(title)
        
        temp = tempfile.TemporaryFile(suffix = ".png")
        temp2 = tempfile.TemporaryFile(suffix = ".png")
        self.wykres.print_png(temp)
        self.wykres2.print_png(temp2)

        images = [Image.open(i) for i in [temp, temp2]]
        widths, heights = zip(*(i.size for i in images))
        max_width = max(widths)
        sum_height = sum(heights)
        new_im = Image.new("RGB", (max_width, sum_height), color = ImageColor.getrgb("#f0f0f0"))
        x_offset = 0
        y_offset = 0
        ile = 0
        for im in images:
            if ile == 1:
                x_offset += 60
            new_im.paste(im, (x_offset, y_offset))
            y_offset += im.size[1]
            ile += 1

        new_im.save(filename)
        self.filemenu.entryconfig(4, state = ACTIVE)

    # zapisuje wynik programu zawierający spektrogram i amplitudę ponownie
    def zapisz(self):
        global title
        global filename

        if filename == "":
            return

        if os.path.isfile(filename) is False:
            messagebox.showerror("Nie można zapisać pliku", "Plik nie istnieje lub został już wcześniej usunięty.")
            self.filemenu.entryconfig(4, state = DISABLED)
            title = "Spektrogram - Bez tytułu 1*"
            self.parent.title(title)
            filename = ""
            return
        
        temp = tempfile.TemporaryFile(suffix = ".png")
        temp2 = tempfile.TemporaryFile(suffix = ".png")
        self.wykres.print_png(temp)
        self.wykres2.print_png(temp2)

        images = [Image.open(i) for i in [temp, temp2]]
        widths, heights = zip(*(i.size for i in images))
        max_width = max(widths)
        sum_height = sum(heights)
        new_im = Image.new("RGB", (max_width, sum_height), color = ImageColor.getrgb("#f0f0f0"))
        x_offset = 0
        y_offset = 0
        ile = 0
        for im in images:
            if ile == 1:
                x_offset += 60
            new_im.paste(im, (x_offset, y_offset))
            y_offset += im.size[1]
            ile += 1

        new_im.save(filename)

        if title[len(title) - 1] == '*':
            title = title[:-1]
            self.parent.title(title)

    # ustawia wybrany okres na spektrogramie i amplitudzie w celu przybliżenia
    def wybierz(self, xmin, xmax):
        data, fs = sf.read(self.file)
        self.xmin = xmin
        self.xmax = xmax
        self.spektrogram.set(xlim = (xmin, xmax))
        self.amplituda.set(xlim = (fs * xmin, fs * xmax))
        self.wykres.draw()
        self.wykres2.draw()
        del self.span

        global title
        if title[len(title) - 1] != '*':
            title += '*'
            self.parent.title(title)

    # wyświetla informacje o tym, jak dokonuje się przybliżenia na spektrogramie
    def przybliz(self):
        global opcja

        if opcja == 0:
            def nie_zamykaj():
                pass

            def zmien(decyzja):
                global opcja
                opcja = decyzja

            top4 = Toplevel()
            top4.title("Przybliżanie")
            top4.protocol("WM_DELETE_WINDOW", nie_zamykaj)
            top4.resizable(False, False)
            top4.focus_force()
            top4.grab_set()
            szer = top4.winfo_screenwidth()
            wys = top4.winfo_screenheight()
            x = int((szer - 450) / 2)
            y = int((wys - 140) / 3)
            top4.geometry("450x140+{0}+{1}".format(x, y))

            label = Label(top4, image = "::tk::icons::information")
            label.place(bordermode = OUTSIDE, x = 15, y = 20)

            etykieta = Label(top4, font = ("TimesNewRoman", "10"), text = "W celu dokonania przybliżenia zaznacz lewym przyciskiem\nmyszy obszar na spektrogramie.")
            etykieta.place(bordermode = OUTSIDE, x = 55, y = 20)

            przycisk = Button(top4, width = 12, height = 1, text = "OK", cursor = "hand2", command = top4.destroy)
            przycisk.place(bordermode = OUTSIDE, x = 340, y = 100)

            decyzja = IntVar()
            check = ttk.Checkbutton(top4, text = "Nie pokazuj tej podpowiedzi więcej w trakcie tej sesji.", variable = decyzja, cursor = "hand2", command = lambda: zmien(decyzja.get()))
            check.place(bordermode = OUTSIDE, x = 15, y = 100)

        self.span = SpanSelector(self.spektrogram, self.wybierz, 'horizontal', useblit = True, rectprops = dict(alpha = 0.5, facecolor = 'red'))

    # oddala wykres spektrogramu i amplitudy do ich początkowej postaci (100 %)
    def oddal(self):
        self.spektrogram.set(xlim = (self.spec_xleft, self.spec_xright))
        self.xmin = self.spec_xleft
        self.xmax = self.spec_xright
        self.amplituda.set(xlim = (self.amp_xleft, self.amp_xright))
        self.wykres.draw()
        self.wykres2.draw()
        global title
        if title[len(title) - 1] != '*':
            title += '*'
            self.parent.title(title)

    # zmienia długość zakładki okien
    def zmien_zakladke(self):
        top6 = Toplevel()
        top6.title("Zmień długość zakładki...")
        top6.resizable(False, False)
        top6.focus_force()
        top6.grab_set()
        szer = top6.winfo_screenwidth()
        wys = top6.winfo_screenheight()
        x = int((szer - 310) / 2)
        y = int((wys - 105) / 3)
        top6.geometry("310x105+{0}+{1}".format(x, y))

        label = Label(top6, font = ("TimesNewRoman", "10"), text = "Długość zakładki:")
        label.place(bordermode = OUTSIDE, x = 10, y = 25)

        self.temp4 = StringVar()
        option = ttk.Combobox(top6, textvariable = self.temp4, state = 'readonly', justify = RIGHT, width = 20)

        if self.nfft == 256:
            option['values'] = ("2", "4", "8", "16", "32", "64", "128")
        elif self.nfft == 1024:
            option['values'] = ("2", "4", "8", "16", "32", "64", "128", "256", "512")
        else:
            option['values'] = ("2", "4", "8", "16", "32", "64", "128", "256", "512", "1024")

        i = 0
        while i < len(option['values']):
            if option['values'][i] == str(self.noverlap):
                option.current(i)
                break
            i += 1
        
        option.place(bordermode = OUTSIDE, x = 150, y = 26)
        option.bind("<<ComboboxSelected>>", lambda event: label.focus())

        # zatwierdza wybrane ustawienie ilości zakładek okien spektrogramu
        def zatwierdz_wybor(wybor):
            self.noverlap = int(wybor)
            if self.typ == 0:
                self.stworz_podstawowy()
            elif self.typ == 1:
                self.stworz_waskopasmowy()
            else:
                self.stworz_szerokopasmowy()
            top6.destroy()

        button = Button(top6, width = 12, height = 1, text = "OK", cursor = "hand2", command = lambda: zatwierdz_wybor(self.temp4.get()))
        button.place(bordermode = OUTSIDE, x = 110, y = 70)

    # tworzy podstawową wersję spektrogramu (taką jak przy wczytywaniu otwartego bądź nagranego pliku)
    def stworz_podstawowy(self):
        self.typ = 0
        data, fs = sf.read(self.file)
        self.nfft = 1024
        if self.noverlap > self.nfft:
            self.noverlap = 512

        if self.window == "hann":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.hann(self.nfft))
        elif self.window == "triang":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.triang(self.nfft))
        elif self.window == "boxcar":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.boxcar(self.nfft))
        elif self.window == "bartlett":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.bartlett(self.nfft))
        elif self.window == "hamming":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.hamming(self.nfft))
        else:
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.blackman(self.nfft))

        self.spektrogram.set(xlim = (self.xmin, self.xmax))
        self.wykres.draw()
        self.viewmenu.entryconfig(0, state = DISABLED, image = self.ikonka6)
        self.viewmenu.entryconfig(1, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(2, state = ACTIVE, image = "")

        global title
        if title[len(title) - 1] != '*':
            title += '*'
            self.parent.title(title)

    # tworzy wąskopasmową wersję spektrogramu
    def stworz_waskopasmowy(self):
        self.typ = 1
        data, fs = sf.read(self.file)
        self.nfft = 2048

        if self.window == "hann":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.hann(self.nfft))
        elif self.window == "triang":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.triang(self.nfft))
        elif self.window == "boxcar":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.boxcar(self.nfft))
        elif self.window == "bartlett":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.bartlett(self.nfft))
        elif self.window == "hamming":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.hamming(self.nfft))
        else:
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.blackman(self.nfft))

        self.spektrogram.set(xlim = (self.xmin, self.xmax))
        self.wykres.draw()
        self.viewmenu.entryconfig(0, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(1, state = DISABLED, image = self.ikonka6)
        self.viewmenu.entryconfig(2, state = ACTIVE, image = "")

        global title
        if title[len(title) - 1] != '*':
            title += '*'
            self.parent.title(title)

    # tworzy szerokopasmową wersję spektrogramu
    def stworz_szerokopasmowy(self):
        self.typ = 2
        data, fs = sf.read(self.file)
        self.nfft = 256
        if self.noverlap > self.nfft:
            self.noverlap = 128

        if self.window == "hann":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.hann(self.nfft))
        elif self.window == "triang":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.triang(self.nfft))
        elif self.window == "boxcar":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.boxcar(self.nfft))
        elif self.window == "bartlett":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.bartlett(self.nfft))
        elif self.window == "hamming":
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.hamming(self.nfft))
        else:
            self.utworz_spektrogram(self.channels, data, fs, okno = windows.blackman(self.nfft))

        self.spektrogram.set(xlim = (self.xmin, self.xmax))
        self.wykres.draw()
        self.viewmenu.entryconfig(0, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(1, state = ACTIVE, image = "")
        self.viewmenu.entryconfig(2, state = DISABLED, image = self.ikonka6)

        global title
        if title[len(title) - 1] != '*':
            title += '*'
            self.parent.title(title)

    # ustawia wybrane przez użytkownika okno wykorzystywane przy tworzeniu spektrogramu
    def ustaw_okno(self, numer):
        i = 4
        while i < 10:
            if i == numer:
                self.viewmenu.entryconfig(i, state = DISABLED, image = self.ikonka6)
                i += 1
                continue
            self.viewmenu.entryconfig(i, state = ACTIVE, image = "")
            i += 1

        data, fs = sf.read(self.file)
        if numer == 4:
            self.window = "hann"
            self.button12.config(state = NORMAL)
            self.button12.update()
            self.button13.config(state = NORMAL)
            self.button13.update()
            self.button14.config(state = NORMAL)
            self.button14.update()
        elif numer == 5:
            self.window = "triang"
            self.button12.config(state = DISABLED)
            self.button12.update()
            self.button13.config(state = NORMAL)
            self.button13.update()
            self.button14.config(state = NORMAL)
            self.button14.update()
        elif numer == 6:
            self.window = "boxcar"
            self.button12.config(state = NORMAL)
            self.button12.update()
            self.button13.config(state = NORMAL)
            self.button13.update()
            self.button14.config(state = NORMAL)
            self.button14.update()
        elif numer == 7:
            self.window = "bartlett"
            self.button12.config(state = NORMAL)
            self.button12.update()
            self.button13.config(state = DISABLED)
            self.button13.update()
            self.button14.config(state = NORMAL)
            self.button14.update()
        elif numer == 8:
            self.window = "hamming"
            self.button12.config(state = NORMAL)
            self.button12.update()
            self.button13.config(state = NORMAL)
            self.button13.update()
            self.button14.config(state = DISABLED)
            self.button14.update()
        else:
            self.window = "blackman"
            self.button12.config(state = NORMAL)
            self.button12.update()
            self.button13.config(state = NORMAL)
            self.button13.update()
            self.button14.config(state = NORMAL)
            self.button14.update()

        if self.typ == 0:
            self.stworz_podstawowy()
        elif self.typ == 1:
            self.stworz_waskopasmowy()
        else:
            self.stworz_szerokopasmowy()

    # zmienia skalę częstotliwości na wykresie spektrogramu
    def zmien_skale(self):
        if self.skala == 'dB':
            self.skala = 'linear'
            self.editmenu.entryconfig(0, state = ACTIVE, image = "")
            self.editmenu.entryconfig(1, state = DISABLED, image = self.ikonka6)
        else:
            self.skala = 'dB'
            self.editmenu.entryconfig(0, state = DISABLED, image = self.ikonka6)
            self.editmenu.entryconfig(1, state = ACTIVE, image = "")

        if self.typ == 0:
            self.stworz_podstawowy()
        elif self.typ == 1:
            self.stworz_waskopasmowy()
        else:
            self.stworz_szerokopasmowy()

    # tworzy spektrogram
    def utworz_spektrogram(self, ilosc, data, fs, okno = windows.hann(1024)):
        def zastapZera(data2):
            i = 0
            while i < len(data2):
                if data2[i] == 0:
                    data2[i] = 10**-10
                i += 1
            return data2

        self.fig.clf()
        self.spektrogram = self.fig.add_subplot(111)
        if ilosc == 1:
            channel = data[:]
        elif ilosc == 2:
            channel = data[:, 0]
        else:
            channel = data[:, 1]
        channel = zastapZera(channel)

        def skala_czas(x, pos):
            return '%1.1fs' % x

        def skala_czest(x, pos):
            return '%1.1fkHz' % (x * 0.001)

        self.pasek.get_tk_widget().place(x = 0.2, y = 520, width = 100, height = 50)
        self.pasek.draw()

        self.spektrogram.specgram(channel, Fs = fs, window = okno, NFFT = self.nfft, noverlap = self.noverlap, scale = self.skala)
        self.spektrogram.set_xlim(xmin = 0, xmax = channel.size / fs)
        self.spektrogram.xaxis.set_visible(True)
        self.spektrogram.xaxis.set_major_formatter(FuncFormatter(skala_czas))
        self.spektrogram.yaxis.set_major_formatter(FuncFormatter(skala_czest))
        self.spektrogram.grid(True)

        self.fig.canvas.mpl_connect('motion_notify_event', self.odczytaj_punkt)
        self.wykres.get_tk_widget().place(x = 38, y = 40, width = 1060)

        self.kanwa.delete('all')
        self.info = self.kanwa.create_text(28, 20, text = "FFT", font = "Times 12")
        self.info = self.kanwa.create_text(21, 40, text = "wn: ", font = "Times 12")
        self.info = self.kanwa.create_text(46, 40, text = " %1.0f" % self.noverlap, font = "Times 12")
        self.info = self.kanwa.create_text(21, 60, text = "wl: ", font = "Times 12")
        self.info = self.kanwa.create_text(46, 60, text = " %1.0f" % self.nfft, font = "Times 12")

        self.kanwa2.delete('all')
        self.info2 = self.kanwa2.create_text(8, 20, text = "F: ", font = "Times 11")
        self.info2 = self.kanwa2.create_text(46, 20, text = "0 Hz", font = "Times 11")
        self.info2 = self.kanwa2.create_text(9, 40, text = "T: ", font = "Times 11")
        self.info2 = self.kanwa2.create_text(47, 40, text = "0 s", font = "Times 11")

    # tworzy amplitudę
    def utworz_amplitude(self, ilosc, data):
        self.fig2.clf()
        self.fig3.clf()
        self.amplituda = self.fig2.add_subplot(111)
        self.amplituda2 = self.fig3.add_subplot(111)
        if ilosc == 1:
            channel = data[:]
        elif ilosc == 2:
            channel = data[:, 0]
        else:
            channel = data[:, 1]

        self.amplituda.plot(channel, color = "green")
        self.amplituda.set(xlim = (0, channel.size))
        self.amplituda.xaxis.set_visible(False)
        self.amplituda.yaxis.set_visible(False)

        self.amplituda2.plot(channel, color = "green")
        self.amplituda2.set(xlim = (0, channel.size))
        self.amplituda2.xaxis.set_visible(False)
        self.amplituda2.yaxis.set_visible(False)

        self.wykres2.get_tk_widget().place(x = 98, y = 530, width = 1000)
        self.wykres2.draw()
        self.wykres3.get_tk_widget().place(x = 98, y = 635, width = 1000)
        self.wykres3.draw()

    # tworzy wykresy spektrogramu i amplitudy
    def utworz_wykresy(self):
        if self.file == "":
            return
        data, fs = sf.read(self.file)
        kanaly = len(data.shape)
        if kanaly == 1:
            self.channels = kanaly
            self.utworz_spektrogram(kanaly, data, fs)
            self.wykres.draw()
            self.utworz_amplitude(kanaly, data)
            self.spec_xleft, self.spec_xright = self.spektrogram.get_xlim()
            self.xmin = self.spec_xleft
            self.xmax = self.spec_xright
            self.amp_xleft, self.amp_xright = self.amplituda.get_xlim()
        else:
            def nie_zamykaj():
                pass

            top2 = Toplevel()
            top2.title("Wybierz kanał...")
            top2.protocol("WM_DELETE_WINDOW", nie_zamykaj)
            top2.resizable(False, False)
            top2.focus_force()
            top2.grab_set()
            szer = top2.winfo_screenwidth()
            wys = top2.winfo_screenheight()
            x = int((szer - 300) / 2)
            y = int((wys - 120) / 3)
            top2.geometry("300x120+{0}+{1}".format(x, y))

            etykieta = Label(top2, font = ("TimesNewRoman", "10"), text = "Wybierz kanał, który chcesz przeanalizować:")
            etykieta.place(bordermode = OUTSIDE, x = 10, y = 10)

            temp = IntVar()
            radio = Radiobutton(top2, text = "1", variable = temp, value = 2)
            radio.place(bordermode = OUTSIDE, x = 70, y = 40)
            radio.select()
            radio2 = Radiobutton(top2, text = "2", variable = temp, value = 3)
            radio2.place(bordermode = OUTSIDE, x = 190, y = 40)
            radio2.deselect()

            def wykonaj_wykresy(kanaly):
                self.channels = kanaly
                self.utworz_spektrogram(kanaly, data, fs)
                self.wykres.draw()
                self.utworz_amplitude(kanaly, data)
                self.spec_xleft, self.spec_xright = self.spektrogram.get_xlim()
                self.xmin = self.spec_xleft
                self.xmax = self.spec_xright
                self.amp_xleft, self.amp_xright = self.amplituda.get_xlim()
                top2.destroy()

            przycisk = Button(top2, width = 12, height = 1, text = "OK", cursor = "hand2", command = lambda: wykonaj_wykresy(temp.get()))
            przycisk.place(bordermode = OUTSIDE, x = 190, y = 80)

    # umożliwia drukowanie wyników programu przez wybraną drukarkę
    def drukuj(self):
        global directory
        temp = tempfile.TemporaryFile(suffix = ".png")
        temp2 = tempfile.TemporaryFile(suffix = ".png")
        self.wykres.print_png(temp)
        self.wykres2.print_png(temp2)

        images = [Image.open(i) for i in [temp, temp2]]
        widths, heights = zip(*(i.size for i in images))
        max_width = max(widths)
        sum_height = sum(heights)
        new_im = Image.new("RGB", (max_width, sum_height), color = ImageColor.getrgb("#f0f0f0"))
        x_offset = 0
        y_offset = 0
        ile = 0
        for im in images:
            if ile == 1:
                x_offset += 60
            new_im.paste(im, (x_offset, y_offset))
            y_offset += im.size[1]
            ile += 1

        nazwa = tempfile.NamedTemporaryFile(suffix = ".png", dir = directory.name, delete = False)
        new_im.save(nazwa)
        win32api.ShellExecute(0, "print", nazwa.name, '/d: "%s"' % win32print.GetDefaultPrinter(), ".", 0)

# wyświetla okno dialogowe przy zamknięciu programu
def zamknij():
    if title[len(title) - 1] == '*':
        top = Toplevel()
        top.title("Zamknij")
        top.resizable(False, False)
        top.focus_set()
        top.grab_set()
        szer = top.winfo_screenwidth()
        wys = top.winfo_screenheight()
        x = int((szer - 450) / 2)
        y = int((wys - 130) / 3)
        top.geometry("450x130+{0}+{1}".format(x, y))

        label = Label(top, image = "::tk::icons::warning")
        label.place(bordermode = OUTSIDE, x = 30, y = 20)

        label2 = Label(top, font = ("TimesNewRoman", "10"), text = "Zapisać zmiany przed zamknięciem programu?")
        label2.place(bordermode = OUTSIDE, x = 80, y = 25)

        def zapisz():
            if title == "Spektrogram - Bez tytułu 1*":
                top.destroy()
                app.zapisz_jako()
                if filename == "":
                    return
                quit()
            else:
                app.zapisz()
                quit()

        przycisk = Button(top, width = 12, height = 1, text = "Zapisz", cursor = "hand2", command = zapisz)
        przycisk.place(bordermode = OUTSIDE, x = 120, y = 80)
        przycisk2 = Button(top, width = 12, height = 1, text = "Nie zapisuj", cursor = "hand2", command = quit)
        przycisk2.place(bordermode = OUTSIDE, x = 220, y = 80)
        przycisk3 = Button(top, width = 12, height = 1, text = "Anuluj", cursor = "hand2", command = top.destroy)
        przycisk3.place(bordermode = OUTSIDE, x = 320, y = 80)
    elif messagebox.askokcancel("Zamknij", "Czy na pewno chcesz zamknąć aplikację?"):
        quit()

if __name__ == "__main__":
    root = Tk()
    root.title(title)
    root.iconphoto(True, PhotoImage(file = "gui\\ikona.png"))
    szer = root.winfo_screenwidth()
    wys = root.winfo_screenheight()
    x = int((szer - 1200) / 2)
    y = int((wys - 750) / 8)
    root.geometry("1200x750+{0}+{1}".format(x, y))
    root.resizable(False, False)
    app = Aplikacja(root)
    root.protocol("WM_DELETE_WINDOW", zamknij)
    root.mainloop()
