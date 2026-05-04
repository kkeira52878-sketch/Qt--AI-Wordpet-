#ifndef VOCABULARYWINDOW_H
#define VOCABULARYWINDOW_H

#include <QWidget>
#include <QVector>
#include "database.h"

class QLineEdit;
class QComboBox;
class QPushButton;
class QLabel;
class QVBoxLayout;
class QGridLayout;

class VocabularyWindow : public QWidget
{
    Q_OBJECT

public:
    explicit VocabularyWindow(QWidget *parent = nullptr);
    ~VocabularyWindow() override;

private slots:
    void onSearchChanged(const QString& text);
    void onFilterChanged(int index);
    void onAddWordClicked();
    void onDeleteWord(int wordId);
    void onToggleFavorite(int wordId);
    void refreshWords();

private:
    void setupUI();
    void loadWords();
    QVector<WordInfo> filterWords(const QVector<WordInfo>& words);

private:
    QLineEdit *m_searchEdit;
    QComboBox *m_filterCombo;
    QPushButton *m_addButton;
    QWidget *m_cardContainer;
    QVBoxLayout *m_cardLayout;
    QLabel *m_statusLabel;

    QVector<WordInfo> m_allWords;
    QString m_currentSearch;
    int m_currentFilter;  // 0=all, 1=mastered, 2=new, 3=favorite
    int m_currentPage;
    static const int ITEMS_PER_PAGE = 20;
};

#endif // VOCABULARYWINDOW_H