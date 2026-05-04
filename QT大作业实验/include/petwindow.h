#ifndef PETWINDOW_H
#define PETWINDOW_H

#include <QWidget>
#include <QLabel>
#include <QPixmap>
#include <QPoint>
#include <QMouseEvent>
#include <QMenu>
#include <QContextMenuEvent>

class PetWindow : public QWidget
{
    Q_OBJECT

public:
    explicit PetWindow(QWidget *parent = nullptr);
    ~PetWindow() override;

public slots:
    void setMood(int mood);  // 0=idle, 1=listening, 2=learning
    void animate();

signals:
    void clicked();
    void doubleClicked();

protected:
    void mousePressEvent(QMouseEvent *event) override;
    void mouseMoveEvent(QMouseEvent *event) override;
    void mouseReleaseEvent(QMouseEvent *event) override;
    void mouseDoubleClickEvent(QMouseEvent *event) override;
    void contextMenuEvent(QContextMenuEvent *event) override;

private:
    void setupUI();
    void loadPetImage();

private:
    QLabel *m_petLabel;
    QPixmap m_petPixmap;
    QPoint m_dragPosition;
    bool m_isDragging;
    int m_mood;
};

#endif // PETWINDOW_H