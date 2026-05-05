#include "vocabularywindow.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QLineEdit>
#include <QComboBox>
#include <QPushButton>
#include <QLabel>
#include <QScrollArea>
#include <QWidget>
#include <QMessageBox>
#include <QInputDialog>
#include <QPainter>
#include <QFrame>
#include <QEvent>
#include <QHoverEvent>

VocabularyWindow::VocabularyWindow(QWidget *parent)
    : QWidget(parent)
    , m_currentFilter(0)
    , m_currentPage(0)
{
    setWindowTitle("词汇库 - WordPet");
    setMinimumSize(800, 600);

    setupUI();
    loadWords();
}

VocabularyWindow::~VocabularyWindow() = default;

void VocabularyWindow::setupUI()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    // Search and filter bar
    QHBoxLayout *topBar = new QHBoxLayout();

    m_searchEdit = new QLineEdit();
    m_searchEdit->setPlaceholderText("搜索单词...");
    m_searchEdit->setMinimumWidth(300);
    connect(m_searchEdit, &QLineEdit::textChanged, this, &VocabularyWindow::onSearchChanged);

    m_filterCombo = new QComboBox();
    m_filterCombo->addItems({"全部", "已掌握", "生词", "收藏"});
    connect(m_filterCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &VocabularyWindow::onFilterChanged);

    m_addButton = new QPushButton("+ 添加单词");
    connect(m_addButton, &QPushButton::clicked, this, &VocabularyWindow::onAddWordClicked);

    topBar->addWidget(m_searchEdit);
    topBar->addWidget(m_filterCombo);
    topBar->addWidget(m_addButton);
    topBar->addStretch();

    mainLayout->addLayout(topBar);

    // Word cards container with scroll
    QScrollArea *scrollArea = new QScrollArea();
    scrollArea->setWidgetResizable(true);
    scrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);

    m_cardContainer = new QWidget();
    m_cardLayout = new QVBoxLayout(m_cardContainer);
    m_cardLayout->setAlignment(Qt::AlignTop);

    scrollArea->setWidget(m_cardContainer);
    mainLayout->addWidget(scrollArea, 1);

    // Status bar
    QHBoxLayout *statusBar = new QHBoxLayout();
    m_statusLabel = new QLabel("共 0 个单词");
    statusBar->addWidget(m_statusLabel);
    statusBar->addStretch();

    mainLayout->addLayout(statusBar);

    setLayout(mainLayout);
}

void VocabularyWindow::loadWords()
{
    m_allWords = Database::instance().getAllWords();
    refreshWords();
}

void VocabularyWindow::refreshWords()
{
    // Clear existing cards
    QLayoutItem *item;
    while ((item = m_cardLayout->takeAt(0)) != nullptr) {
        if (item->widget()) {
            item->widget()->deleteLater();
        }
        delete item;
    }

    // Filter words
    QVector<WordInfo> filtered = filterWords(m_allWords);
    m_statusLabel->setText(QString("共 %1 个单词").arg(filtered.size()));

    // Create word cards
    int cardCount = 0;
    for (const WordInfo& word : filtered) {
        if (cardCount >= ITEMS_PER_PAGE) break;

        QFrame *card = new QFrame();
        card->setFrameStyle(QFrame::Box);
        card->setLineWidth(1);
        card->setStyleSheet("QFrame { background: white; border-radius: 8px; padding: 10px; }");

        QVBoxLayout *cardLayout = new QVBoxLayout(card);

        // Word and favorite button
        QHBoxLayout *titleRow = new QHBoxLayout();
        QLabel *wordLabel = new QLabel(word.word);
        wordLabel->setStyleSheet("font-size: 18px; font-weight: bold; color: #2E5A8C;");

        QPushButton *favBtn = new QPushButton(word.is_favorite ? "★" : "☆");
        favBtn->setStyleSheet("border: none; font-size: 20px; color: gold;");
        connect(favBtn, &QPushButton::clicked, this, [this, word.id]() { onToggleFavorite(word.id); });

        titleRow->addWidget(wordLabel);
        titleRow->addWidget(favBtn);
        titleRow->addStretch();

        // Phonetic
        QLabel *phoneticLabel = new QLabel(word.phonetic);
        phoneticLabel->setStyleSheet("color: #666; font-style: italic;");

        // Definition
        QLabel *defLabel = new QLabel(word.definition);
        defLabel->setWordWrap(true);
        defLabel->setStyleSheet("color: #333;");

        // Example
        if (!word.example.isEmpty()) {
            QLabel *exampleLabel = new QLabel(word.example);
            exampleLabel->setStyleSheet("color: #888; font-style: italic;");
            cardLayout->addWidget(exampleLabel);
        }

        // Delete button
        QPushButton *deleteBtn = new QPushButton("删除");
        deleteBtn->setStyleSheet("QPushButton { background: #ff6b6b; color: white; border: none; padding: 5px 10px; border-radius: 4px; }");
        connect(deleteBtn, &QPushButton::clicked, this, [this, word.id]() { onDeleteWord(word.id); });

        cardLayout->addLayout(titleRow);
        cardLayout->addWidget(phoneticLabel);
        cardLayout->addWidget(defLabel);
        cardLayout->addWidget(deleteBtn);

        m_cardLayout->addWidget(card);
        cardCount++;
    }
}

QVector<WordInfo> VocabularyWindow::filterWords(const QVector<WordInfo>& words)
{
    QVector<WordInfo> result = words;

    // Apply search filter
    if (!m_currentSearch.isEmpty()) {
        result = Database::instance().searchWords(m_currentSearch);
    }

    // Apply category filter
    QVector<WordInfo> filtered;
    for (const WordInfo& word : result) {
        switch (m_currentFilter) {
            case 1: // mastered
                if (word.mastery >= 4) filtered.append(word);
                break;
            case 2: // new
                if (word.mastery == 0) filtered.append(word);
                break;
            case 3: // favorite
                if (word.is_favorite) filtered.append(word);
                break;
            default:
                filtered.append(word);
        }
    }

    return filtered;
}

void VocabularyWindow::onSearchChanged(const QString& text)
{
    m_currentSearch = text;
    refreshWords();
}

void VocabularyWindow::onFilterChanged(int index)
{
    m_currentFilter = index;
    refreshWords();
}

void VocabularyWindow::onAddWordClicked()
{
    bool ok;
    QString word = QInputDialog::getText(this, "添加单词", "请输入单词:", QLineEdit::Normal, "", &ok);
    if (ok && !word.isEmpty()) {
        QString phonetic = QInputDialog::getText(this, "添加单词", "请输入音标:", QLineEdit::Normal, "", &ok);
        if (ok) {
            QString definition = QInputDialog::getText(this, "添加单词", "请输入释义:", QLineEdit::Normal, "", &ok);
            if (ok) {
                QString example = QInputDialog::getText(this, "添加单词", "请输入例句(可选):", QLineEdit::Normal, "", &ok);
                Database::instance().addWord(word, phonetic, definition, example);
                loadWords();
            }
        }
    }
}

void VocabularyWindow::onDeleteWord(int wordId)
{
    QMessageBox msgBox;
    msgBox.setText("确定要删除这个单词吗?");
    msgBox.setStandardButtons(QMessageBox::Yes | QMessageBox::No);
    msgBox.setDefaultButton(QMessageBox::No);

    if (msgBox.exec() == QMessageBox::Yes) {
        Database::instance().deleteWord(wordId);
        loadWords();
    }
}

void VocabularyWindow::onToggleFavorite(int wordId)
{
    Database::instance().toggleFavorite(wordId);
    loadWords();
}