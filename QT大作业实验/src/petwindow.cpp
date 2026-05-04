#include "petwindow.h"
#include <QPainter>
#include <QPainterPath>
#include <QPropertyAnimation>
#include <QGraphicsDropShadowEffect>

PetWindow::PetWindow(QWidget *parent)
    : QWidget(parent)
    , m_isDragging(false)
    , m_mood(0)
{
    setWindowFlags(Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint | Qt::Tool);
    setAttribute(Qt::WA_TranslucentBackground);
    setFixedSize(120, 120);

    setupUI();

    // Start idle animation
    QPropertyAnimation *anim = new QPropertyAnimation(this, "windowOpacity");
    anim->setDuration(2000);
    anim->setStartValue(1.0);
    anim->setEndValue(0.8);
    anim->setDirection(QPropertyAnimation::Alternate);
    anim->setLoopCount(-1);
    anim->start();
}

PetWindow::~PetWindow() = default;

void PetWindow::setupUI()
{
    m_petLabel = new QLabel(this);
    m_petLabel->setFixedSize(120, 120);
    m_petLabel->setAlignment(Qt::AlignCenter);

    loadPetImage();
}

void PetWindow::loadPetImage()
{
    // Create a cute pet image using stylesheet
    QString moodColor;
    switch (m_mood) {
        case 0: moodColor = "#4A90D9"; break;  // Idle - blue
        case 1: moodColor = "#FFD700"; break;  // Listening - gold
        case 2: moodColor = "#50C878"; break;  // Learning - green
        default: moodColor = "#4A90D9";
    }

    // Create rounded pet body
    m_petLabel->setStyleSheet(QString(R"(
        QLabel {
            background-color: %1;
            border-radius: 60px;
            border: 3px solid #2E5A8C;
        }
    )").arg(moodColor));

    // Simple emoji-like representation using text
    QString emoji;
    switch (m_mood) {
        case 0: emoji = "(^_^)"; break;   // Idle
        case 1: emoji = "(o_o)"; break;  // Listening
        case 2: emoji = "(^_^)/"; break; // Learning
        default: emoji = "(^_^)";
    }

    // Create a visual representation
    QFont font("Microsoft YaHei", 16, QFont::Bold);
    m_petLabel->setFont(font);

    // Use a border image simulation via stylesheet
}

void PetWindow::setMood(int mood)
{
    m_mood = mood;
    loadPetImage();
}

void PetWindow::animate()
{
    // Floating animation handled in constructor
}

void PetWindow::mousePressEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        m_dragPosition = event->globalPos() - frameGeometry().topLeft();
        m_isDragging = false;
    }
}

void PetWindow::mouseMoveEvent(QMouseEvent *event)
{
    if (event->buttons() & Qt::LeftButton) {
        move(event->globalPos() - m_dragPosition);
        m_isDragging = true;
    }
}

void PetWindow::mouseReleaseEvent(QMouseEvent *event)
{
    if (!m_isDragging && event->button() == Qt::LeftButton) {
        emit clicked();
    }
    m_isDragging = false;
}

void PetWindow::mouseDoubleClickEvent(QMouseEvent *event)
{
    Q_UNUSED(event);
    emit doubleClicked();
}

void PetWindow::contextMenuEvent(QContextMenuEvent *event)
{
    QMenu menu;
    menu.addAction("设置", this, &QWidget::hide);
    menu.addAction("关于", this, []() {
        QMessageBox::about(nullptr, "关于 WordPet",
            "WordPet - AI英语单词学习桌宠\n\n"
            "一个可爱的桌面宠物帮助你学习英语单词。\n"
            "版本: 1.0");
    });
    menu.addSeparator();
    menu.addAction("退出", qApp, &QApplication::quit);

    menu.exec(event->globalPos());
}