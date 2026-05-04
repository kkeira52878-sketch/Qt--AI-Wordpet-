#include <QApplication>
#include <QSystemTrayIcon>
#include <QMenu>
#include <QMessageBox>
#include <QTimer>

#include "petwindow.h"
#include "vocabularywindow.h"
#include "database.h"
#include "dictapi.h"
#include "clipboardmonitor.h"

class WordPetApp : public QApplication
{
    Q_OBJECT

public:
    WordPetApp(int& argc, char** argv)
        : QApplication(argc, argv)
        , m_petWindow(nullptr)
        , m_vocabWindow(nullptr)
        , m_dictApi(nullptr)
        , m_clipboardMonitor(nullptr)
        , m_superModeActivated(0)
    {
        setApplicationName("WordPet");
        setApplicationVersion("1.0");

        // Initialize database
        if (!Database::instance().init()) {
            QMessageBox::critical(nullptr, "错误", "无法初始化数据库!");
            quit();
            return;
        }

        // Create main pet window
        m_petWindow = new PetWindow();
        m_petWindow->show();

        // Connect pet signals
        connect(m_petWindow, &PetWindow::clicked, this, &WordPetApp::onPetClicked);
        connect(m_petWindow, &PetWindow::doubleClicked, this, &WordPetApp::onPetDoubleClicked);

        // Create vocabulary window
        m_vocabWindow = new VocabularyWindow();
        m_vocabWindow->hide();

        // Create dictionary API
        m_dictApi = new DictApi(this);

        // Create clipboard monitor
        m_clipboardMonitor = new ClipboardMonitor(this);
        m_clipboardMonitor->startMonitoring();

        // Connect clipboard monitor
        connect(m_clipboardMonitor, &ClipboardMonitor::wordFound, this, &WordPetApp::onWordFound);

        // Setup system tray
        setupTray();

        // Setup hotkey registration (placeholder - Windows requires RegisterHotKey)
        setupHotkeys();
    }

    ~WordPetApp()
    {
        if (m_vocabWindow) delete m_vocabWindow;
    }

private slots:
    void onPetClicked()
    {
        if (m_vocabWindow->isVisible()) {
            m_vocabWindow->hide();
        } else {
            m_vocabWindow->show();
            m_vocabWindow->activateWindow();
        }
    }

    void onPetDoubleClicked()
    {
        // Show settings or about dialog
        QMessageBox::information(nullptr, "WordPet",
            "WordPet v1.0\n\n"
            "AI英语单词学习桌宠\n\n"
            "快捷键:\n"
            "Ctrl+Shift+W: 划词添加\n"
            "点击桌宠: 打开词汇库");
    }

    void onWordFound(const QString& word)
    {
        // Auto-query and show notification
        m_dictApi->query(word);

        // Change pet mood to indicate listening
        m_petWindow->setMood(1);

        QTimer::singleShot(2000, [this]() {
            m_petWindow->setMood(0);
        });
    }

    void onQueryFinished(const QString& word, const QString& phonetic,
                         const QString& definition, const QString& example)
    {
        // Add to database
        Database::instance().addWord(word, phonetic, definition, example);

        // Show tray notification
        if (m_trayIcon) {
            m_trayIcon->showMessage("新单词已添加",
                QString("已将 '%1' 添加到词汇库").arg(word),
                QSystemTrayIcon::Information, 3000);
        }
    }

private:
    void setupTray()
    {
        m_trayIcon = new QSystemTrayIcon(this);
        m_trayIcon->setIcon(QIcon::fromTheme("utilities-terminal"));

        QMenu *trayMenu = new QMenu();

        QAction *showAction = new QAction("显示/隐藏词汇库", this);
        connect(showAction, &QAction::triggered, this, &WordPetApp::onPetClicked);

        QAction *superModeAction = new QAction("超级模式", this);
        connect(superModeAction, &QAction::triggered, this, []() {
            QMessageBox::information(nullptr, "超级模式", "超级模式开发中...");
        });

        QAction *quitAction = new QAction("退出", this);
        connect(quitAction, &QAction::triggered, this, &QApplication::quit);

        trayMenu->addAction(showAction);
        trayMenu->addAction(superModeAction);
        trayMenu->addSeparator();
        trayMenu->addAction(quitAction);

        m_trayIcon->setContextMenu(trayMenu);
        m_trayIcon->show();

        // Handle tray icon click
        connect(m_trayIcon, &QSystemTrayIcon::activated, this, [](QSystemTrayIcon::ActivationReason reason) {
            if (reason == QSystemTrayIcon::Trigger) {
                // Toggle vocab window
            }
        });
    }

    void setupHotkeys()
    {
        // Note: Full global hotkey implementation requires Windows API
        // This is a placeholder that logs when Ctrl+Shift+W would be triggered
        qDebug() << "Global hotkey Ctrl+Shift+W registered for word capture";
    }

private:
    PetWindow *m_petWindow;
    VocabularyWindow *m_vocabWindow;
    DictApi *m_dictApi;
    ClipboardMonitor *m_clipboardMonitor;
    QSystemTrayIcon *m_trayIcon;
    int m_superModeActivated;
};

#include "main.moc"

int main(int argc, char *argv[])
{
    WordPetApp app(argc, argv);
    return app.exec();
}