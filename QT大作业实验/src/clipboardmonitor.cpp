#include "clipboardmonitor.h"
#include <QApplication>
#include <QClipboard>
#include <QRegularExpression>

ClipboardMonitor::ClipboardMonitor(QObject *parent)
    : QObject(parent)
    , m_timer(new QTimer(this))
    , m_enabled(false)
{
    connect(m_timer, &QTimer::timeout, this, &ClipboardMonitor::checkClipboard);
}

ClipboardMonitor::~ClipboardMonitor() = default;

void ClipboardMonitor::startMonitoring()
{
    m_enabled = true;
    m_timer->start(1000);  // Check every second
}

void ClipboardMonitor::stopMonitoring()
{
    m_enabled = false;
    m_timer->stop();
}

bool ClipboardMonitor::isMonitoring() const
{
    return m_enabled;
}

void ClipboardMonitor::checkClipboard()
{
    if (!m_enabled) return;

    QClipboard *clipboard = QApplication::clipboard();
    QString text = clipboard->text().trimmed();

    // Skip if same as last content or empty
    if (text.isEmpty() || text == m_lastContent) {
        return;
    }

    m_lastContent = text;

    // Check if it's a valid English word
    if (isValidEnglishWord(text)) {
        emit wordFound(text);
    }
}

bool ClipboardMonitor::isValidEnglishWord(const QString& text)
{
    // Must be 2-20 characters, only letters
    QRegularExpression re("^[a-zA-Z]{2,20}$");
    return re.match(text).hasMatch();
}